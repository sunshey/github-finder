# cloudflare/ai 项目分析

- GitHub: https://github.com/cloudflare/ai
- 分析日期: 2026-09-17
- 仓库状态: Cloudflare 官方仓库，MIT License，主语言 TypeScript

## 一句话结论

`cloudflare/ai` 是 Cloudflare 官方维护的 AI SDK/adapter monorepo，用来把 Workers AI、AI Gateway、AI Search 等 Cloudflare AI 能力接入 Vercel AI SDK、TanStack AI、Workers 应用和 MCP/Agent 示例。

它值得关注，尤其适合研究“AI 基础设施平台如何把模型推理、网关、搜索/RAG、MCP 和前端 AI SDK 统一成开发者可用的 provider 层”。它不是一个单一产品应用，而是一组 npm 包、示例和 demo 的集合。

## 它是做什么的

仓库 README 将它定位为 Cloudflare 上构建 AI 应用的 packages and examples，主要包含：

1. Vercel AI SDK Provider
   - `workers-ai-provider`: 将 Cloudflare Workers AI 包装成 Vercel AI SDK provider。
   - 支持 chat、image generation、embeddings、transcription、text-to-speech、reranking。
   - 同时支持通过 AI Gateway 路由第三方模型。

2. AI Gateway Provider
   - `ai-gateway-provider`: 将 OpenAI、Anthropic、Google、Grok、OpenRouter 等模型请求统一路由到 Cloudflare AI Gateway。
   - 支持缓存、重试、fallback、BYOK、metadata、Zero Data Retention 等 Gateway 功能。

3. AI Search Provider
   - `ai-search-provider`: 将 Cloudflare AI Search 接入 AI SDK。
   - 支持上传文件建立索引、自然语言搜索、生成 grounded chat response。

4. TanStack AI Adapter
   - `@cloudflare/tanstack-ai`: 面向 TanStack AI 的 Cloudflare adapter。
   - 支持 Workers AI 和 AI Gateway，覆盖 chat、image、transcription、TTS、summarization 等能力。

5. Examples / Demos
   - `examples/workers-ai`: Workers AI playground。
   - `examples/tanstack-ai`: TanStack AI 多 provider 示例。
   - `demos/`: 包含 tool calling、structured output、agents、MCP servers、OAuth MCP、remote MCP 等大量 Cloudflare Workers 示例。

## 实现原理

核心设计是“Cloudflare AI 平台能力 + 标准 AI SDK provider/adapter 层”。

1. Workers AI provider
   - `createWorkersAI(options)` 是主要入口。
   - 在 Worker 内部推荐传入 `env.AI` binding，无需 API key。
   - 在 Worker 外部可传入 `accountId` 和 `apiKey` 走 REST API。
   - 返回一个 provider 函数，按模型类型创建不同 model wrapper：
     - `chat(...)`
     - `textEmbedding(...)`
     - `image(...)`
     - `transcription(...)`
     - `speech(...)`
     - `reranking(...)`

2. AI Gateway 路由
   - 对 Cloudflare 内部模型，可通过 `gateway` 参数把请求路由到 AI Gateway。
   - 对第三方模型，使用 provider plugin 将 `openai/gpt-*`、`anthropic/...` 等 catalog slug 路由到 Gateway。
   - Gateway 层负责缓存、metadata、日志、fallback、BYOK、统一计费等能力。

3. AI Gateway provider for Vercel AI SDK
   - `createAiGateway(options)` 会包装一个或多个 `@ai-sdk/*` model。
   - 它通过拦截底层 provider 的 request，转换为 AI Gateway universal endpoint 所需格式。
   - 多模型数组可实现 fallback，Gateway 返回的 `cf-aig-step` 决定最终使用哪个模型响应。

4. 共享 gateway-core
   - `packages/gateway-core` 是内部共享核心，不单独发布。
   - 它集中维护 provider registry、header 构造、gateway fetch、resumable stream、Workers AI SSE helpers、错误处理等。
   - 其他包在构建时将它 bundle 进去，避免多个包复制一套 Gateway 逻辑。

5. AI Search
   - `ai-search-provider` 包装 `ai_search_namespaces` Workers binding。
   - 通过 namespace/instance 模型管理索引。
   - `instance.chat()` 可作为 AI SDK model 使用，`instance.search()` 做直接搜索，`items.upload()` 管理索引内容。

## 技术栈与结构

- TypeScript: 主要实现语言，约 1.22 MB。
- 包管理: pnpm 11。
- 构建/工程: Nx、tsdown、Changesets。
- 测试: Vitest，包含 unit test 和 e2e test。
- Cloudflare 相关: Wrangler、Workers AI binding、AI Gateway binding、AI Search binding、Workers OAuth、MCP SDK。

主要目录：

- `packages/workers-ai-provider/`: Vercel AI SDK 的 Workers AI provider。
- `packages/ai-gateway-provider/`: Vercel AI SDK 的 AI Gateway provider。
- `packages/ai-search-provider/`: AI Search provider。
- `packages/tanstack-ai/`: TanStack AI adapter。
- `packages/gateway-core/`: 内部共享 Gateway 核心。
- `examples/`: 可运行示例。
- `demos/`: 面向 Agent、MCP、tool calling、workflow 等场景的 Cloudflare Workers demos。
- `docs/`: 包间关系、gateway routing、binding vs REST、各包使用说明。

## 是否值得关注

值得关注，理由：

1. Cloudflare 官方维护，和 Workers AI / AI Gateway / AI Search 的平台演进同步。
2. 它不是简单 demo，而是包含可发布 npm 包、测试、文档、示例和 release 流程的 monorepo。
3. 对 AI 应用工程化很有参考价值：provider abstraction、binding vs REST、Gateway fallback、BYOK、缓存、metadata、resumable streaming 都有落地代码。
4. MCP、remote MCP auth、Agent demos 很多，适合学习 Cloudflare Workers 上的 AI Agent 架构。
5. 适合观察 Cloudflare 如何把自家 AI 平台接入 Vercel AI SDK、TanStack AI 等主流上层生态。

需要注意：

1. 许多能力和 Cloudflare 账号、Workers binding、AI Gateway 配置强绑定。
2. 部分能力明确标注为 experimental 或 coming soon，例如某些 Gateway delegate、resumable streaming。
3. 仓库是 monorepo，示例很多，初看会比较散；最好从 `packages/workers-ai-provider` 和 `packages/ai-gateway-provider` 入手。
4. 不是通用 AI 应用模板，更适合作为 Cloudflare AI 平台集成层参考。

## 关注评级

推荐关注: 4.6 / 5

适合关注的人：

- 正在用 Cloudflare Workers / Workers AI / AI Gateway 构建 AI 应用的开发者。
- 想研究 AI SDK provider 设计的人。
- 想在边缘计算环境里做 AI Agent、MCP server、tool calling 的开发者。
- 想理解 AI Gateway 如何承载缓存、fallback、BYOK、日志与统一计费的人。

不太适合的人：

- 完全不使用 Cloudflare 生态的人。
- 想找一个开箱即用的终端用户 AI 产品。
- 只需要极简 OpenAI API wrapper 的项目。

## 数据依据

- 仓库元数据: 1165 stars、347 forks、99 open issues、MIT License、默认分支 `main`，更新时间 2026-09-16T09:25:08+08:00，最近 push 2026-09-11T23:54:08+08:00。
- README: https://github.com/cloudflare/ai/blob/main/README.md
- Workers AI provider: https://github.com/cloudflare/ai/tree/main/packages/workers-ai-provider
- AI Gateway provider: https://github.com/cloudflare/ai/tree/main/packages/ai-gateway-provider
- AI Search provider: https://github.com/cloudflare/ai/tree/main/packages/ai-search-provider
- TanStack AI adapter: https://github.com/cloudflare/ai/tree/main/packages/tanstack-ai
- Gateway core: https://github.com/cloudflare/ai/tree/main/packages/gateway-core
