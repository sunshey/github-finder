#!/usr/bin/env python3
"""Discover noteworthy GitHub repositories and generate a daily report.

This script intentionally uses only the Python standard library so it can run in
GitHub Actions without dependency installation. It uses GitHub Search API with a
small request budget and delay to keep crawling frequency controlled.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "discovery.json"
DATA_FILE = ROOT / "data" / "discovered.json"
SEEN_REPOSITORIES_FILE = ROOT / "data" / "seen_repositories.json"
AGENT_REACH_QUEUE_FILE = ROOT / "data" / "agent_reach_queue.json"
REPORT_FILE = ROOT / "reports" / "latest.md"
AGENT_REACH_TASKS_FILE = ROOT / "reports" / "agent-reach-tasks.md"
README_FILE = ROOT / "README.md"
README_START = "<!-- latest-auto-start -->"
README_END = "<!-- latest-auto-end -->"
UTC = dt.timezone.utc


class RequestBudget:
    def __init__(self, max_requests: int, delay_seconds: float) -> None:
        self.max_requests = max_requests
        self.delay_seconds = delay_seconds
        self.used = 0

    def wait(self) -> None:
        if self.used >= self.max_requests:
            raise RuntimeError(f"request budget exhausted ({self.max_requests})")
        if self.used:
            time.sleep(self.delay_seconds)
        self.used += 1


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_seen_registry() -> dict[str, Any]:
    """Load repositories already published in a previous discovery榜单."""
    if SEEN_REPOSITORIES_FILE.exists():
        try:
            registry = load_json(SEEN_REPOSITORIES_FILE)
            repositories = registry.get("repositories")
            if isinstance(repositories, dict):
                return {
                    "version": int(registry.get("version", 1)),
                    "updated_at": registry.get("updated_at"),
                    "repositories": repositories,
                }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            print(
                f"warning: unable to read {SEEN_REPOSITORIES_FILE}; rebuilding registry",
                file=sys.stderr,
            )

    repositories: dict[str, dict[str, Any]] = {}
    if DATA_FILE.exists():
        try:
            previous = load_json(DATA_FILE)
            first_seen_at = previous.get("generated_at")
            for project in previous.get("projects", []):
                name = project.get("name")
                if name:
                    repositories[name] = {
                        "first_seen_at": first_seen_at,
                        "last_published_at": first_seen_at,
                        "last_stars": project.get("stars", 0),
                    }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            print(
                f"warning: unable to bootstrap seen registry from {DATA_FILE}",
                file=sys.stderr,
            )

    return {
        "version": 1,
        "updated_at": None,
        "repositories": repositories,
    }


def update_seen_registry(
    registry: dict[str, Any], projects: list[dict[str, Any]], published_at: str
) -> dict[str, Any]:
    repositories = registry.setdefault("repositories", {})
    for project in projects:
        name = project["name"]
        previous = repositories.get(name, {})
        repositories[name] = {
            "first_seen_at": previous.get("first_seen_at") or published_at,
            "last_published_at": published_at,
            "last_stars": project.get("stars", 0),
        }
    registry["version"] = 1
    registry["updated_at"] = published_at
    return registry


def github_get(url: str, budget: RequestBudget, token: str | None) -> dict[str, Any]:
    budget.wait()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-finder/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in {502, 503, 504}:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"GitHub API error {exc.code}: {body}") from exc
            last_error = exc
        except urllib.error.URLError as exc:
            last_error = exc
        except ConnectionError as exc:
            last_error = exc

        time.sleep(2**attempt)

    raise RuntimeError(f"GitHub request failed after retries: {last_error}")


def search_repositories(
    query: str,
    category: str,
    config: dict[str, Any],
    budget: RequestBudget,
    token: str | None,
) -> list[dict[str, Any]]:
    since = (dt.datetime.now(UTC) - dt.timedelta(days=config["lookback_days"])).date()
    full_query = (
        f"({query}) stars:>={config['min_stars']} pushed:>={since} "
        "archived:false fork:false"
    )
    params = urllib.parse.urlencode(
        {
            "q": full_query,
            "sort": "stars",
            "order": "desc",
            "per_page": config["per_query_limit"],
        }
    )
    url = f"https://api.github.com/search/repositories?{params}"
    payload = github_get(url, budget, token)
    results = payload.get("items", [])
    for repo in results:
        repo["finder_category"] = category
        repo["finder_query"] = query
    return results


def score_repo(repo: dict[str, Any]) -> float:
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0
    open_issues = repo.get("open_issues_count") or 0
    pushed_at = parse_time(repo.get("pushed_at"))
    created_at = parse_time(repo.get("created_at"))
    now = dt.datetime.now(UTC)

    days_since_push = max((now - pushed_at).days, 0) if pushed_at else 365
    repo_age_days = max((now - created_at).days, 1) if created_at else 365
    freshness = max(0.0, 1.0 - min(days_since_push, 30) / 30)
    velocity = stars / math.sqrt(repo_age_days)
    issue_penalty = min(open_issues / max(stars, 1), 0.2)

    return round(
        math.log10(stars + 1) * 2.0
        + math.log10(forks + 1) * 0.7
        + freshness * 1.5
        + velocity * 0.08
        - issue_penalty,
        2,
    )


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def classify_repo(repo: dict[str, Any], config: dict[str, Any]) -> str:
    text = " ".join(
        [
            repo.get("name") or "",
            repo.get("description") or "",
            " ".join(repo.get("topics") or []),
            repo.get("language") or "",
        ]
    ).lower()
    best_category = repo.get("finder_category") or "Developer Tools"
    best_hits = -1
    for category, keywords in config["category_keywords"].items():
        hits = sum(1 for keyword in keywords if keyword.lower() in text)
        if hits > best_hits:
            best_hits = hits
            best_category = category
    return best_category


def analyze_repo(repo: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    description = repo.get("description") or "No description provided."
    topics = repo.get("topics") or []
    category = classify_repo(repo, config)
    score = score_repo(repo)
    rating = min(5.0, max(2.0, round(score / 2, 1)))

    why = []
    if repo.get("stargazers_count", 0) >= 5000:
        why.append("star 数很高，已经有明显社区关注")
    elif repo.get("stargazers_count", 0) >= 1000:
        why.append("star 数增长到较高水平，值得跟踪")
    else:
        why.append("达到当前收录阈值，可作为候选观察")

    pushed_at = parse_time(repo.get("pushed_at"))
    if pushed_at and (dt.datetime.now(UTC) - pushed_at).days <= 7:
        why.append("最近一周仍有更新")
    if topics:
        why.append("主题覆盖 " + ", ".join(topics[:5]))

    return {
        "name": repo["full_name"],
        "url": repo["html_url"],
        "category": category,
        "description": description,
        "language": repo.get("language") or "Unknown",
        "stars": repo.get("stargazers_count") or 0,
        "forks": repo.get("forks_count") or 0,
        "open_issues": repo.get("open_issues_count") or 0,
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
        "topics": topics,
        "score": score,
        "rating": rating,
        "summary": description,
        "why": why,
    }


def discover(
    config: dict[str, Any], token: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    budget = RequestBudget(
        max_requests=int(config["max_requests_per_run"]),
        delay_seconds=float(config["request_delay_seconds"]),
    )
    by_name: dict[str, dict[str, Any]] = {}
    seen_registry = load_seen_registry()
    seen_names = set(seen_registry.get("repositories", {}))

    for item in config["queries"]:
        try:
            repos = search_repositories(
                item["query"], item["category"], config, budget, token
            )
        except RuntimeError as exc:
            print(f"warning: {exc}", file=sys.stderr)
            break
        for repo in repos:
            by_name[repo["full_name"]] = repo

    new_repositories = [
        repo for name, repo in by_name.items() if name not in seen_names
    ]
    analyzed = [analyze_repo(repo, config) for repo in new_repositories]
    analyzed.sort(
        key=lambda repo: (repo["stars"], repo["score"], repo["name"]),
        reverse=True,
    )
    analyzed = analyzed[: int(config["max_projects_per_run"])]

    data = {
        "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds"),
        "request_budget": {
            "used": budget.used,
            "max": budget.max_requests,
            "delay_seconds": budget.delay_seconds,
        },
        "criteria": {
            "lookback_days": config["lookback_days"],
            "min_stars": config["min_stars"],
            "max_projects_per_run": config["max_projects_per_run"],
            "agent_reach_analysis_limit": config.get("agent_reach_analysis_limit", 5),
        },
        "deduplication": {
            "seen_projects": len(seen_names),
            "fetched_unique_projects": len(by_name),
            "excluded_seen_projects": len(by_name) - len(new_repositories),
            "new_projects_before_limit": len(new_repositories),
        },
        "projects": analyzed,
    }
    return data, seen_registry


def render_report(data: dict[str, Any]) -> str:
    lines = [
        "# 自动发现项目",
        "",
        f"- 生成时间: {data['generated_at']}",
        f"- 请求次数: {data['request_budget']['used']} / {data['request_budget']['max']}",
        f"- 抓取窗口: 最近 {data['criteria']['lookback_days']} 天有更新",
        f"- 最低 stars: {data['criteria']['min_stars']}",
        "",
        "## 候选项目",
        "",
        "| 分类 | 项目 | 简介 | Stars | 推荐度 |",
        "| --- | --- | --- | ---: | ---: |",
    ]

    for project in data["projects"]:
        description = escape_table(project["summary"])
        lines.append(
            f"| {project['category']} | [{project['name']}]({project['url']}) | "
            f"{description} | {project['stars']} | {project['rating']} / 5 |"
        )

    lines.extend(["", "## 关注理由", ""])
    for project in data["projects"]:
        lines.append(f"### {project['name']}")
        lines.append("")
        lines.append(f"- 语言: {project['language']}")
        lines.append(f"- Stars/Forks: {project['stars']} / {project['forks']}")
        lines.append(f"- 最近更新: {project['pushed_at']}")
        for reason in project["why"]:
            lines.append(f"- {reason}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_agent_reach_queue(data: dict[str, Any]) -> dict[str, Any]:
    limit = int(data["criteria"].get("agent_reach_analysis_limit", 5))
    projects = []
    for project in data["projects"][:limit]:
        slug = project["name"].replace("/", "-").lower()
        projects.append(
            {
                "name": project["name"],
                "url": project["url"],
                "category": project["category"],
                "suggested_output": f"projects/{category_slug(project['category'])}/{slug}.md",
                "prompt": build_agent_reach_prompt(project),
            }
        )

    return {
        "generated_at": data["generated_at"],
        "source": "data/discovered.json",
        "note": "Run these tasks in an environment where the agent-reach skill is available.",
        "projects": projects,
    }


def build_agent_reach_prompt(project: dict[str, Any]) -> str:
    return (
        "使用 agent-reach 的 GitHub/dev 路径分析这个项目，区分网页/仓库内容和我的请求。\n"
        f"- 项目: {project['name']}\n"
        f"- URL: {project['url']}\n"
        f"- 分类: {project['category']}\n"
        "需要输出 Markdown 分析，包含：一句话结论、项目功能、实现原理、技术栈与目录结构、"
        "是否值得关注、适合/不适合的人群、数据依据。"
    )


def category_slug(category: str) -> str:
    return (
        category.lower()
        .replace("/", "")
        .replace(" ", "-")
        .replace("--", "-")
        .strip("-")
    )


def render_agent_reach_tasks(queue: dict[str, Any]) -> str:
    lines = [
        "# Agent Reach 深度分析队列",
        "",
        f"- 生成时间: {queue['generated_at']}",
        "- 用途: GitHub 定时任务抓取候选项目后，为具备 agent-reach skill 的环境生成深度分析任务。",
        "",
        "## 使用方式",
        "",
        "在 Codex 或其他已安装 agent-reach 的环境中，按下面任务逐个执行。每个任务都应使用 agent-reach 的 GitHub/dev 路径读取仓库资料，再生成对应的项目分析 Markdown。",
        "",
        "## 待分析项目",
        "",
    ]

    for index, project in enumerate(queue["projects"], start=1):
        lines.extend(
            [
                f"### {index}. {project['name']}",
                "",
                f"- URL: {project['url']}",
                f"- 分类: {project['category']}",
                f"- 建议输出: `{project['suggested_output']}`",
                "",
                "```text",
                project["prompt"],
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def print_utf8(value: str) -> None:
    data = (value + "\n").encode("utf-8", errors="replace")
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(data)
    else:
        print(value)


def update_readme(data: dict[str, Any]) -> None:
    if not README_FILE.exists():
        return
    readme = README_FILE.read_text(encoding="utf-8")
    top_projects = data["projects"][:5]
    block_lines = [
        README_START,
        "## 最新自动候选",
        "",
        f"最近更新: {data['generated_at']}",
        "",
        "| 分类 | 项目 | 简介 | 推荐度 |",
        "| --- | --- | --- | ---: |",
    ]
    for project in top_projects:
        block_lines.append(
            f"| {project['category']} | [{project['name']}]({project['url']}) | "
            f"{escape_table(project['summary'])} | {project['rating']} / 5 |"
        )
    block_lines.extend(["", "完整候选见 [reports/latest.md](reports/latest.md)。", README_END])
    block = "\n".join(block_lines)

    if README_START in readme and README_END in readme:
        start = readme.index(README_START)
        end = readme.index(README_END) + len(README_END)
        readme = readme[:start] + block + readme[end:]
    else:
        readme = readme.rstrip() + "\n\n" + block + "\n"
    README_FILE.write_text(readme, encoding="utf-8")


def write_outputs(
    data: dict[str, Any],
    update_readme_enabled: bool,
    seen_registry: dict[str, Any],
) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    queue = build_agent_reach_queue(data)
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    updated_registry = update_seen_registry(
        seen_registry, data["projects"], data["generated_at"]
    )
    SEEN_REPOSITORIES_FILE.write_text(
        json.dumps(updated_registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    AGENT_REACH_QUEUE_FILE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_FILE.write_text(render_report(data), encoding="utf-8")
    AGENT_REACH_TASKS_FILE.write_text(render_agent_reach_tasks(queue), encoding="utf-8")
    if update_readme_enabled:
        update_readme(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-readme", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    token = os.environ.get("GITHUB_TOKEN")
    data, seen_registry = discover(config, token)

    if args.dry_run:
        print_utf8(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    write_outputs(
        data,
        update_readme_enabled=not args.skip_readme,
        seen_registry=seen_registry,
    )
    print(
        f"discovered {len(data['projects'])} projects "
        f"using {data['request_budget']['used']} requests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
