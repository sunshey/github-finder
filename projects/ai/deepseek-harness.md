# deepseek-ai/deepseek-harness 项目分析

- GitHub: https://github.com/deepseek-ai/deepseek-harness
- 官方文档: https://deepseek-harness.github.io/deepseek-harness/
- 官网: https://deepseek.com/harness
- 分析日期: 2026-09-17
- 仓库状态: DeepSeek AI 官方仓库，MIT，主语言 TypeScript，当前为 developer preview

## 一句话结论

`deepseek-ai/deepseek-harness` 是 DeepSeek AI 官方开源的 Agent Harness，命令行名称为 `dsh`。它不是单一聊天 UI 或模型 wrapper，而是一个以 Cordis 为底座、强调 "everything is a plugin" 的 Agent 运行时与产品框架，覆盖 Web UI、headless、SDK、ACP automation、桌面应用、工具调用、会话日志、沙箱、审批、插件和 profile/bundle 组合。

它非常值得关注，尤其适合研究下一代 Agent 产品的工程架构：如何把模型适配器、工具注册、会话持久化、系统提示词、Agent loop、文件系统、子进程、沙箱、审批策略和 UI 都设计成可组合、可替换、可卸载的能力。但它仍处于 developer preview，官方明确提示会有破坏性变更，也不能把它当作已审计的生产安全边界。

## 它是做什么的

DeepSeek Harness 提供一个可运行、可扩展的本地 Agent 环境：

1. 通过 `npx @deepseek-ai/dsh web` 启动本地 Web UI，默认监听 `http://127.0.0.1:3080`。
2. 通过 profile 启动不同形态的应用，例如 `web`、`headless`、`sdk`、`sdk-minimal`、`acp`。
3. 通过 plugin/bundle/profile 机制组合能力，而不是把功能写死在单一核心里。
4. 支持模型适配、工具注册、会话日志、系统提示词组装、沙箱与审批、文件系统与子进程能力、MCP、webhook、subagent、goal、schedule、workflow 等 Agent 产品常见模块。
5. 同时包含 Web 前端、CLI、Electron desktop、Python SDK runtime、网站文档和大量测试/快照。

它的定位更接近一个 Agent 操作系统或 Agent 产品底座，而不是只解决一次模型调用的 SDK。

## 实现原理

项目架构的核心是 Cordis 插件树。

1. Everything is a plugin
   - 官方架构文档说明：模型 adapter、tool registry、session log、agent loop 本身都是插件。
   - 插件向共享 context 贡献 service、typed event 和 reversible effect。
   - 扩展行为不需要 patch 特权核心，而是挂载插件；插件卸载时对应注册会回滚。

2. Profile 与 bundle 分层
   - 一个运行中的 `dsh` 是启动时组合出来的插件树。
   - profile 描述要叠加哪些 bundle、安装哪些外部插件，以及用户自己的 `cordis.patch.yml`。
   - bundle 是 Cordis 配置行和代码的分发格式。
   - 官方提供 `web`、`headless`、`sdk`、`sdk-minimal`、`acp` 等 profile 模板。

3. 多入口但统一启动
   - 所有 Node 应用都从 `dsh` CLI 以 profile 方式启动。
   - `dsh web` 是 `--profile web` 的便捷别名。
   - SDK、headless、ACP automation 都走同一个 profile/patch 组合模型，而不是另建孤立应用。
   - Desktop 版本使用 Electron，并携带匹配的 dsh runtime 和客户端图。

4. 事件驱动的 Agent loop
   - durable session event 记录 turn、step、system/user/assistant message、tool call/result 等事实。
   - live agent event 处理 `agent/pre-step`、`agent/request`、`agent/assistant-stream`、`agent/turn-stopping` 等运行时扩展点。
   - 工具调用经过 `tools/pre-execute`、`tools/execute`、`tools/post-execute` 管线。
   - 模型可见内容必须可从 session log 重建，这是它处理可追溯性和恢复能力的关键。

5. Capability seam
   - 文件系统、子进程、shell、terminal、sandbox、tools、LLM、subagent、webhook 等能力通过 service definition + provider + consumer 的方式解耦。
   - 替换 provider 可以改变整条能力链，例如把本地 shell/PTY/LSP 切到远程 sandbox，而上层工具不需要 fork。

## 技术栈与结构

- 主语言: TypeScript
- 包管理: pnpm 11
- Node 要求: 22.19+ 或 24+
- 构建: TypeScript project references、tsdown、Vite/VitePress、tsx
- 测试: Vitest、Playwright、快照测试、Web stress/perf 配置
- 桌面端: Electron
- 原生模块: `native/system`
- 文档: VitePress，包含英文和中文文档
- 许可证: MIT

主要目录和模块：

- `apps/cli`: `@deepseek-ai/dsh` CLI，负责 profile boot、plugin management 和 Web UI alias。
- `apps/desktop`: Electron 桌面应用。
- `packages/core/session`: append-only session event log 和内存 store。
- `packages/core/system-prompt`: prompt section 与 tool schema 组装。
- `packages/core/tools`: scoped tool registry 与 guarded execution pipeline。
- `packages/core/agent`: Agent interface、live registry、agent events。
- `packages/core/agent-loop`: 默认 Agent driver。
- `packages/llm/llm`: LLM 消息、stream vocabulary 和 adapter seam。
- `packages/bundle/base`: web/headless/sdk/acp 的共享基础层。
- `packages/bundle/web-app`: 浏览器应用层。
- `packages/bundle/headless`: 一次性无 server runner。
- `packages/bundle/sdk-app` / `sdk-minimal`: SDK 运行形态。
- `packages/bundle/acp-app`: automation-only ACP server。
- `website`: 官方文档站。
- `vendor`: vendored Cordis 相关包。
- `.agents/notes`: 大量架构决策、流程和实现说明。

## 是否值得关注

非常值得关注，理由：

1. 官方背景强：DeepSeek AI 官方发布，天然具备生态关注度。
2. 工程野心大：把 Agent 产品拆成可组合插件树，而不是只做模型调用 SDK。
3. 架构参考价值高：profile/bundle、event pipeline、session log、capability seam、工具执行管线、沙箱与审批策略都值得单独研究。
4. 产品形态完整：Web UI、CLI、headless、SDK、ACP、desktop、文档和测试体系都已经在仓库中。
5. 插件生态方向明确：官方鼓励第三方插件使用 `dsh-plugin` topic，项目结构也围绕插件发现和组合展开。

需要注意：

1. 官方明确标注 developer preview，会有破坏性兼容变更。
2. 安全说明明确指出项目可以执行模型生成的代码和命令、加载第三方插件、访问网络/进程/凭据/文件；不能把 sandbox、审批和权限控制当作绝对隔离。
3. 仓库体量巨大，学习成本高，建议从 README、`docs/architecture.md`、`apps/cli/package.json`、核心 packages 和 bundle 文档入手。
4. 它更像 Agent runtime/product framework，不适合只想要轻量模型 API wrapper 的场景。

## 关注评级

推荐关注: 4.8 / 5

适合关注的人：

- 正在研究 Agent runtime、Agent IDE、自动化 Agent 产品的人。
- 想理解插件化 Agent 架构、会话日志、工具调用管线和能力隔离的人。
- 希望比较 Claude Code、Codex、OpenCode、Vercel AI SDK、MCP 生态之外另一种 Agent 产品底座的人。
- 想围绕 DeepSeek 生态做本地 Agent、自动化、插件或 SDK 集成的人。

不太适合的人：

- 只需要一个简单 LLM API SDK 的开发者。
- 需要稳定生产 API 且不能接受破坏性变更的团队。
- 想把它直接作为不可信代码执行沙箱的人。

## 数据依据

- 仓库元数据: 227161 stars、27071 forks、0 open issues、MIT、默认分支 `master`，创建时间 2026-08-13T19:56:32+08:00，最近 push 2026-09-15T12:51:11+08:00。
- 语言分布: TypeScript 约 38.8 MB，CSS 约 0.53 MB，Python 约 0.43 MB，JavaScript 约 0.25 MB，另有 C、Shell、C++、PowerShell、HTML、Batchfile、NSIS。
- Topics: `ai-agents`、`cordis`、`dsh`、`dsh-plugin`。
- README: https://github.com/deepseek-ai/deepseek-harness/blob/master/README.md
- 架构文档: https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md
- 开发文档: https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/development.md
- 安全说明: https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md
- CLI 包: https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/package.json
