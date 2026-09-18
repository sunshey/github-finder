# ZhuLinsen/daily_stock_analysis 项目分析

- GitHub: https://github.com/ZhuLinsen/daily_stock_analysis
- 产品站: https://dsa.zhulinsen.tech
- 分析日期: 2026-09-18
- 仓库状态: MIT，主语言 Python，同时包含 React/TypeScript Web 前端和 Electron 桌面端

## 一句话结论

`daily_stock_analysis` 是一个 LLM 驱动的多市场股票智能分析系统，面向 A 股、港股、美股、日股、韩股、台股和 ETF，提供行情与基本面数据聚合、新闻搜索、技术分析、多 Agent 决策报告、选股、回测、持仓和多渠道推送。

它的价值不在于某一个指标或某一个模型，而在于把股票研究流程包装成可自动运行的产品：数据源有 fallback，分析任务有交易日判断和断点续传，LLM 可以通过多 Agent 分阶段处理，结果可以进入 Web 工作台、API、桌面端、GitHub Actions 或通知渠道。需要明确的是，它是研究和决策辅助工具，不是自动交易系统，也不代表分析结论可靠或构成投资建议。

## 它是做什么的

项目围绕“自选股每日分析”组织能力：

1. 输入自选股代码，获取历史行情、实时或近实时行情、K 线、技术指标、基本面、新闻、公告和市场上下文。
2. 通过技术分析、情报分析、风险分析和决策 Agent 汇总为决策仪表盘。
3. 输出核心结论、评分、趋势、买卖点位、风险警报、催化因素和操作检查清单。
4. 支持 A 股、港股、美股、日股、韩股、台股和 ETF，但不同市场的数据能力并不完全相同。
5. 支持手动分析、每日定时分析、大盘复盘、Agent 策略问股、选股、回测、历史报告、持仓管理和告警。
6. 将报告推送到企业微信、飞书、Telegram、Discord、Slack、邮件、钉钉、PushPlus、ntfy、Gotify、Server 酱等渠道。

因此它更像一个“个人量化研究与投研工作台”，而不只是一个调用大模型生成股票摘要的脚本。

## 实现原理

### 1. 多源行情和故障切换

项目通过 `DataFetcherManager` 统一管理行情数据源，依赖中可以看到大致的 fallback 链：

- `efinance`
- `AkShare`
- `Tushare`
- `Pytdx`
- `Baostock`
- `YFinance`
- `Longbridge`
- `TickFlow`
- `Futu OpenAPI`（主要用于读取持仓）

免费数据源可以零配置运行，但会受到上游限流、接口变更和网络波动影响。付费或 token 型数据源可以补充稳定性和市场覆盖，但需要自行配置账号和密钥。

### 2. 分阶段股票分析流水线

`src/core/pipeline.py` 是单股分析的主要调度器，负责协调：

1. 从本地数据库或远程数据源获取并保存行情。
2. 检查断点续传，复用当前交易日已经保存的数据。
3. 获取实时行情、量比、换手率和可选的筹码分布。
4. 执行均线、趋势、量价等传统技术分析。
5. 通过搜索服务获取最新新闻、风险信息和业绩预期。
6. 组装分析上下文并交给传统分析器或 Agent 分支。
7. 生成报告、落盘、记录诊断信息并向通知渠道推送。

流水线还会根据指数和市场能力矩阵跳过不适用的模块，避免把 A 股专属的资金流、龙虎榜或板块字段错误套用到海外市场。

### 3. 多 Agent 编排

`src/agent/orchestrator.py` 将一个分析任务拆成多个阶段：

- `quick`: Technical -> Decision
- `standard`: Technical -> Intel -> Decision
- `full`: Technical -> Intel -> Risk -> Decision
- `specialist`: Technical -> Intel -> Risk -> specialist evaluation -> Decision

各阶段共享 `AgentContext`，并通过工具注册表读取行情、新闻、回测、市场和组合信息。编排器具备最大步骤数、总超时、分 Agent 超时、预算不足降级、工具调用记录和最终输出解析等机制。

最终决策不是简单地把模型原文拼接起来。项目还会执行风险覆盖：当风险标记触发时，可以把模型生成的 `buy` 调整为 `hold` 或 `sell`，并同步修正操作建议、仓位建议和风险说明。

### 4. 数据与报告闭环

项目使用 SQLite/SQLAlchemy 保存行情、分析历史、回测、组合、告警、决策信号和 Agent 相关样本。报告可以渲染成 Markdown、图片或不同通知渠道所需的格式。

报告中保留分析上下文、模型调用、数据质量和降级信息，这使得历史结果、信号表现和风险覆盖可以继续被评估，而不是每次运行都只产生一段不可追踪的文本。

### 5. 自动化运行

`.github/workflows/00-daily-analysis.yml` 默认在周一到周五 UTC 10:00，也就是北京时间 18:00 运行，并支持手动触发：

- `full`: 股票分析 + 大盘复盘
- `market-only`: 只做大盘复盘
- `stocks-only`: 只做股票分析

工作流还配置了：

- 同一时间只运行一个分析任务的 concurrency group。
- 0 到 60 秒随机启动延迟，避免固定时间集中访问数据源。
- 30 分钟默认超时。
- 交易日检查，非交易日自动跳过。
- 分析报告和日志上传为 GitHub Actions artifact。
- 多个 LLM、行情、搜索和通知服务的环境变量入口。

这使它可以在 GitHub Actions 上低成本定时运行，但免费服务的稳定性和 API 配额仍取决于外部供应商。

## 技术栈与结构

- 后端: Python 3.10+
- Web/API: FastAPI、Uvicorn
- 前端: React、TypeScript、Vite
- 桌面端: Electron
- 数据处理: Pandas、NumPy
- 数据库: SQLAlchemy、SQLite
- LLM: LiteLLM、OpenAI SDK，兼容 Gemini、Anthropic、OpenAI/DeepSeek、通义千问、Claude、Ollama 等
- 搜索: Tavily、SerpAPI、Bocha、Brave、MiniMax、SearXNG 等
- 报告: Jinja2、Markdown、可选 Markdown 转图片
- 测试: pytest，以及 Web 前端的 Vitest/Playwright 测试
- 自动化: GitHub Actions、Docker、本地 scheduler

主要目录：

- `main.py`: CLI 主入口，支持单次分析、定时、Web/API、回测和大盘复盘。
- `src/core/pipeline.py`: 股票分析主流水线。
- `src/agent/`: Agent 上下文、工具、技能、策略和多 Agent 编排。
- `data_provider/`: 多市场行情数据源和 fallback 管理。
- `src/services/screening/`: 选股和候选股票排序。
- `src/services/`: 分析、回测、告警、组合、搜索、通知等服务层。
- `api/`: FastAPI API。
- `apps/dsa-web/`: React Web 工作台。
- `apps/dsa-desktop/`: Electron 桌面端。
- `.github/workflows/00-daily-analysis.yml`: GitHub Actions 每日分析任务。
- `strategies/`: 技术分析和选股策略 YAML。

## 是否值得关注

值得关注，理由：

1. 产品闭环完整：从行情采集、搜索、分析、风控、报告到通知和历史评估都有对应模块。
2. 多市场适配意识较强：项目明确记录了不同市场的数据源和能力边界，而不是简单把 A 股字段复制到所有市场。
3. Agent 工程化程度较高：有专门的编排器、工具面、技能、超时、预算、风险接管和可观测信息。
4. 自动化门槛低：GitHub Actions、Docker、本地 Web/API 和定时任务都已经准备好。
5. 工程参考价值高：适合研究如何将 LLM 接入一个已有的数据处理、策略分析和通知系统。
6. 生态关注度高：截至分析时仓库拥有 65,226 stars、54,582 forks，且持续更新。

需要注意：

1. 金融数据具有时效性和供应商依赖，免费源可能限流、延迟、字段缺失或发生接口变化。
2. LLM 生成的新闻归纳、风险判断和交易建议可能出现幻觉、遗漏或过度自信。
3. 多市场虽然覆盖面广，但各市场的实时行情、基本面、行业、资金流和市场宽度能力并不对齐。
4. 项目有较多可选 provider、环境变量和运行模式，首次部署需要阅读完整配置文档。
5. 它没有替用户承担交易执行、合规、资金管理和投资决策责任。

## 关注评级

推荐关注: 4.8 / 5

适合关注的人：

- 想搭建个人投研、股票日报或市场复盘系统的开发者。
- 研究 LLM + 金融数据 + Agent workflow 的工程师。
- 希望理解多数据源 fallback、交易日历、回测、通知和 Web 工作台如何组合的人。
- 想在 GitHub Actions 或 Docker 中低成本运行个人分析任务的人。

不太适合的人：

- 只需要一个简单行情 API wrapper 的开发者。
- 期待系统自动稳定盈利或直接替代专业投顾的人。
- 需要完整实时行情、低延迟交易和券商自动下单能力的团队。

## 数据依据

- 仓库元数据: 65,226 stars、54,582 forks、47 open issues、MIT，默认分支 `main`。
- 仓库时间: 创建于 2026-01-10，最近更新于 2026-09-18，最近 push 于 2026-09-13。
- Topics: `a-stock`、`ai-agent`、`aigc`、`llm`、`quant`、`quantitative-finance`、`quantitative-trading`。
- 语言分布: Python 约 13.2 MB，TypeScript 约 3.3 MB，另有 JavaScript、CSS、Shell、Jinja、PowerShell、HTML、Dockerfile 和 NSIS。
- README: https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/README.md
- 市场支持边界: https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/docs/market-support.md
- 每日工作流: https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/.github/workflows/00-daily-analysis.yml
- 核心流水线: https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/src/core/pipeline.py
- Agent 编排器: https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/src/agent/orchestrator.py
- 相关论文: https://arxiv.org/abs/2608.26990

## 风险提示

项目 README 已明确声明仅供学习和研究使用，不构成任何投资建议。使用时应自行核验行情、新闻和财务数据，不应把 LLM 报告、回测结果或模型评分直接视为买卖指令。不要把 API 密钥、券商凭据或私人通知 webhook 暴露到公开仓库；将 Web/API 暴露到公网时也应启用认证并配置可信网络边界。
