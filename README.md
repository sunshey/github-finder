# GitHub Finder

发现值得关注的 GitHub 项目，并按领域分类汇总。

这个仓库记录高质量开源项目：它们可能有很强的工程参考价值、产品启发、生态位置，或代表某个技术方向正在发生的变化。


## 项目索引

| 分类 | 项目 | 简介 | 推荐度 |
| --- | --- | --- | --- |
| AI / Agent | [stripe/ai](projects/ai/stripe-ai.md) | Stripe 官方面向 AI Agent 的 SDK、MCP、插件和技能集合，用于把支付、计费、Connect 等能力接入主流 Agent 框架。 | 4.5 / 5 |

## 分类说明

- `AI / Agent`: Agent 工具、MCP、LLM 应用框架、AI 工程化项目。
- `Developer Tools`: 提升开发、调试、部署、自动化效率的工具。
- `Infrastructure`: 数据库、缓存、队列、网络、云原生、可观测性等基础设施。
- `Frontend`: 前端框架、组件库、设计工具、交互体验相关项目。
- `Productivity`: 面向个人或团队效率提升的应用和工具。

## 收录标准

- 项目有明确应用场景或工程价值。
- 项目实现方式有参考意义。
- 项目活跃度、作者背景、生态位置或技术路线值得跟踪。

## 自动发现

仓库内置了一个轻量自动发现工具：[scripts/discover_github.py](scripts/discover_github.py)。

它会每天通过 GitHub Search API 抓取近期活跃、达到 star 阈值的项目，按分类打分并生成候选汇总：

- 汇总数据: [data/discovered.json](data/discovered.json)
- 最新报告: [reports/latest.md](reports/latest.md)
- Agent Reach 分析队列: [data/agent_reach_queue.json](data/agent_reach_queue.json)
- Agent Reach 任务说明: [reports/agent-reach-tasks.md](reports/agent-reach-tasks.md)
- 定时任务: [.github/workflows/daily-discovery.yml](.github/workflows/daily-discovery.yml)

抓取频率和阈值在 [config/discovery.json](config/discovery.json) 中配置，默认包含：

- 每天运行 1 次。
- 只看最近 14 天仍有更新的项目。
- 最低 star 阈值为 300。
- 每次最多输出 12 个候选项目。
- 每次最多生成 5 个 Agent Reach 深度分析任务。
- 每次最多 24 个 GitHub API 请求。
- 每次请求之间等待 2 秒，避免高频抓取。

GitHub Actions 负责自动抓取候选项目和生成 Agent Reach 分析队列。深度分析需要在安装了 `agent-reach` skill 的环境中执行，按 [reports/agent-reach-tasks.md](reports/agent-reach-tasks.md) 里的任务逐个生成正式项目分析。

## 推荐度说明

- `5 / 5`: 强烈推荐，值得持续跟踪或深入研究。
- `4 / 5`: 值得关注，对特定方向有明显参考价值。
- `3 / 5`: 有亮点，但适用场景或成熟度有限。
- `2 / 5`: 暂时观望，记录但不建议投入太多时间。

<!-- latest-auto-start -->
## 最新自动候选

最近更新: 2026-09-17T03:44:18+00:00

| 分类 | 项目 | 简介 | 推荐度 |
| --- | --- | --- | ---: |
| AI / Agent | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | DeepSeek Harness: Everything is a Plugin. | 5.0 / 5 |
| AI / Agent | [openclaw/openclaw](https://github.com/openclaw/openclaw) | The AI that really does things. Any OS. Any Platform. The lobster way. 🦞 | 5.0 / 5 |
| AI / Agent | [mattpocock/skills](https://github.com/mattpocock/skills) | Skills for Real Engineers. Straight from my .agents directory. | 5.0 / 5 |
| AI / Agent | [affaan-m/ECC](https://github.com/affaan-m/ECC) | The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond. | 5.0 / 5 |
| AI / Agent | [obra/superpowers](https://github.com/obra/superpowers) | An agentic skills framework & software development methodology that works. | 5.0 / 5 |

完整候选见 [reports/latest.md](reports/latest.md)。
<!-- latest-auto-end -->
