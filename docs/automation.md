# 自动发现机制说明

这份文档记录本项目的自动发现流程。它用于维护者查看，不展示在 README 首页。

## 运行方式

GitHub Actions 会每天自动运行一次：

- Workflow: `.github/workflows/daily-discovery.yml`
- Cron: `15 1 * * *`
- 北京时间: 每天 09:15 左右
- 也可以在 GitHub Actions 页面手动触发 `Daily GitHub Discovery`

## 抓取逻辑

自动发现脚本位于：

- `scripts/discover_github.py`

脚本通过 GitHub Search API 抓取近期活跃项目，然后按 star、fork、最近更新时间、仓库年龄、issue 比例等指标生成候选列表。

默认配置位于：

- `config/discovery.json`

当前默认配置：

- 最近 14 天仍有更新的项目。
- 最低 star 阈值为 300。
- 每个查询最多抓取 8 个项目。
- 每次最多输出 12 个候选项目。
- 每次最多生成 5 个 Agent Reach 深度分析任务。
- 每次最多 24 个 GitHub API 请求。
- 每次请求之间等待 2 秒，避免高频抓取。

## 输出文件

自动发现会生成这些文件：

- `data/discovered.json`: 结构化候选项目数据。
- `reports/latest.md`: 最新候选项目报告。
- `data/agent_reach_queue.json`: Agent Reach 深度分析队列。
- `reports/agent-reach-tasks.md`: 给具备 agent-reach skill 的环境使用的分析任务说明。

README 中只展示 `latest-auto` 区块里的最新候选项目，不展示自动发现机制说明。

## Agent Reach 分析

GitHub Actions 默认 runner 没有本机 Codex skills / agent-reach 环境，因此定时任务不会直接执行深度分析。

当前流程是：

1. GitHub Actions 定时抓取候选项目。
2. 脚本生成 `data/agent_reach_queue.json` 和 `reports/agent-reach-tasks.md`。
3. 在安装了 `agent-reach` skill 的环境中，按任务说明逐个分析项目。
4. 分析结果写入 `projects/<category>/<repo>.md`。
5. 人工确认后再更新 README 的正式项目索引。

## 本地运行

```bash
python scripts/discover_github.py
```

只预览不写文件：

```bash
python scripts/discover_github.py --dry-run
```

运行后如果生成了新的候选结果，确认内容合理后再提交。
