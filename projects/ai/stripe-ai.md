# stripe/ai 项目分析

- GitHub: https://github.com/stripe/ai
- 官网文档: https://docs.stripe.com/agents
- 分析日期: 2026-09-17
- 仓库状态: Stripe 官方仓库，MIT License，主语言 TypeScript

## 一句话结论

`stripe/ai` 是 Stripe 面向 AI Agent 场景的官方工具集合。它把 Stripe 的支付、计费、Connect、客户等能力包装成 LLM/Agent 可调用的工具，面向 Vercel AI SDK、LangChain、OpenAI Agents、CrewAI、MCP、Codex、Claude Code、Cursor、Grok 等生态。

它值得关注，尤其适合研究“传统 SaaS/支付 API 如何接入 Agent 工具调用生态”。但它不是一个可直接运行的完整业务应用，更像 SDK、MCP 代理、Agent 插件和最佳实践技能的集合。

## 它是做什么的

仓库 README 将它定位为“building AI-powered products and businesses on top of Stripe”的一站式入口，主要包含这些部分：

1. SDK 和 Toolkit
   - `@stripe/agent-toolkit`: TypeScript 包，用于把 Stripe 工具接入 LangChain、Vercel AI SDK、OpenAI、MCP。
   - `stripe-agent-toolkit`: Python 包，用于接入 OpenAI Agents SDK、LangChain、CrewAI、Strands。
   - `@stripe/ai-sdk`、`@stripe/token-meter`: 面向 AI SDK 和 token 计量/计费的库。

2. MCP 能力
   - Stripe 提供远端 MCP 服务: `https://mcp.stripe.com`。
   - 本仓库里的 toolkit 可以连接远端 MCP 服务，获取可用工具，再转成本地 Agent 框架可识别的工具格式。

3. Agent 插件和技能
   - 仓库包含 Claude、Codex、Cursor、Grok、Agent Plugins 等不同客户端的插件目录。
   - `skills/` 和 `providers/*/plugin/skills/` 下包含 Stripe 最佳实践、Connect 推荐、Stripe Apps、升级迁移等 Agent 指令包。

4. Benchmarks / evals
   - `benchmarks/` 下有 checkout、支付迁移、Stripe 集成等任务环境和 grader，用于评估 Agent 完成 Stripe 集成任务的能力。

## 实现原理

核心设计是“远端 MCP 服务 + 本地框架适配器”。

1. 连接远端 MCP
   - TypeScript 的 `StripeMcpClient` 使用 `@modelcontextprotocol/sdk` 连接 `MCP_SERVER_URL`。
   - 请求头里带 `Authorization: Bearer <Stripe key>`。
   - 如果配置了 Connect 账号上下文，会带 `Stripe-Account`。
   - API key 校验接受 `sk_*` 和 `rk_*`，并明确建议使用 restricted key `rk_*`。

2. 动态发现工具
   - 连接成功后调用 MCP 的 `listTools()` 获取工具列表。
   - 工具可用性由 Stripe 侧根据 restricted key 权限过滤，而不是在本地硬编码全部 Stripe API。

3. 框架适配
   - `ToolkitCore` 是 TypeScript 共享基类，负责初始化 MCP 客户端、获取远端工具、缓存工具列表。
   - 不同目录只负责把 MCP tool schema 转成目标框架格式：
     - `src/ai-sdk/toolkit.ts`: 转成 Vercel AI SDK 的 `tool(...)`。
     - `src/openai/toolkit.ts`: 转成 OpenAI function/tool calling 的 `ChatCompletionTool[]`。
     - `src/modelcontextprotocol/toolkit.ts`: 注册成本地 MCP server 的 proxy tool。
     - `src/langchain/toolkit.ts`: 转成 LangChain 工具。

4. 工具调用代理
   - Agent 选择某个工具后，本地 toolkit 调用 `mcpClient.callTool(name, args)`。
   - `callTool` 将参数转发给 `mcp.stripe.com`，并把返回的 text content 交给 Agent。
   - 如果配置了 `customer` 上下文，会自动注入或覆盖参数里的 customer。

5. Schema 转换
   - 远端 MCP 工具返回 JSON Schema。
   - 本地通过 `schema-utils` 转成 Zod schema 或 OpenAI function parameters，使不同 Agent 框架可以直接验证和展示参数。

## 技术栈与结构

- TypeScript: 主要实现语言，约 910k bytes。
- Python: Python Agent Toolkit，约 213k bytes。
- Ruby / JavaScript / HTML / CSS / Shell: 主要来自 benchmarks、示例项目和测试环境。
- 关键依赖:
  - `@modelcontextprotocol/sdk`
  - `stripe`
  - `zod`
  - `ai`
  - `openai`
  - `@langchain/core`

主要目录：

- `tools/typescript/`: TypeScript Agent Toolkit。
- `tools/python/`: Python Agent Toolkit。
- `tools/modelcontextprotocol/`: MCP server/extension 相关工具。
- `skills/`: 通用 Stripe Agent skills。
- `providers/`: 各 Agent 客户端插件封装。
- `benchmarks/`: Agent 集成 Stripe 的评测任务。
- `llm/`: AI SDK、token meter 等 LLM 计费集成。

## 是否值得关注

值得关注，理由：

1. Stripe 官方维护，可信度高。
2. 仓库活跃，2026-09-17 仍有 push。
3. 明确覆盖当前主流 Agent 接入方式: MCP、OpenAI tools、Vercel AI SDK、LangChain、Claude/Codex/Cursor/Grok 插件。
4. 设计上把敏感 API 能力放在 Stripe 远端 MCP 服务侧，客户端只做权限 key、schema 适配和调用代理，安全边界比较清晰。
5. benchmarks 对研究 Agent 工程化评测有参考价值。

需要注意：

1. 它依赖 Stripe 账号和 API key，真实使用前要配置权限，最好用 restricted key。
2. 工具能力并非完整 Stripe API，本地包说明也强调不是 exhaustive。
3. TypeScript 新版本采用异步初始化，旧式直接访问 `tools` 会得到迁移警告。
4. 因为关键工具列表来自远端 MCP，离线阅读源码不能完整知道当前所有可用 Stripe tools。

## 关注评级

推荐关注: 4.5 / 5

适合关注的人：

- 正在做 AI Agent + 支付/订阅/计费/商业化能力的开发者。
- 想研究 MCP 远端服务如何落地到实际 API 平台的人。
- 想给 Codex、Claude Code、Cursor 等 Agent 提供领域技能和工具的人。

不太适合的人：

- 只想找一个开箱即用的 SaaS 模板。
- 不使用 Stripe 或不需要真实支付/计费集成。
- 想要本地完全自包含、离线可运行的 Agent 工具集。

## 数据依据

- 仓库元数据: 1821 stars、342 forks、88 open issues、MIT License、默认分支 `main`，更新时间 2026-09-17T00:49:01Z。
- README: https://github.com/stripe/ai/blob/main/README.md
- TypeScript toolkit: https://github.com/stripe/ai/tree/main/tools/typescript
- Python toolkit: https://github.com/stripe/ai/tree/main/tools/python
- MCP 文档: https://docs.stripe.com/mcp
