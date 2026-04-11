# Phase 4: Capability Invocation Tracing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 04-capability-invocation-tracing
**Areas discussed:** Capability 注册方式, MCP 集成方式, Trace 事件格式与投递, Run 关联 ID 与追踪存储

---

## Capability 注册方式

| Option | Description | Selected |
|--------|-------------|----------|
| 框架原生 Tool 注册 | 使用 agentscope-runtime 框架提供的 tool 注册机制（如 @app.tool 或 agent.tool()） | ✓ |
| 自定义注册层 | 自定义工具注册层，在 query handler 中动态注册 | |
| 混合方式 | 简单工具用框架原生，MCP 用自定义 | |

**User's choice:** 框架原生 Tool 注册
**Notes:** 与 ReActAgent 集成紧密，减少胶水代码

| Option | Description | Selected |
|--------|-------------|----------|
| 包含示例工具 | 包含具体示例工具（如 get_weather, calculate）用于端到端验证 | ✓ |
| 纯基础设施，无示例工具 | 只实现基础设施，用户自己注册工具 | |

**User's choice:** 包含示例工具
**Notes:** 确保测试时可实际触发工具调用

| Option | Description | Selected |
|--------|-------------|----------|
| 启动时固定注册 | 服务启动时注册一次，所有请求共享 | ✓ |
| 请求级别动态注册 | 每个请求可指定工具子集 | |

**User's choice:** 启动时固定注册
**Notes:** 适合 R&D 测试场景，简单直接

---

## MCP 集成方式

| Option | Description | Selected |
|--------|-------------|----------|
| agentscope 内置 MCP 支持 | 使用 agentscope-runtime 内置 MCP 支持注册 MCP server/tool | ✓ |
| MCP SDK 独立集成 | 使用 modelcontextprotocol SDK 单独建立 MCP client | |
| 延后 MCP 到专门 phase | Phase 4 只做 tool/skill 追踪 | |

**User's choice:** agentscope 内置 MCP 支持
**Notes:** 一体化，无额外依赖

| Option | Description | Selected |
|--------|-------------|----------|
| 本地示例 MCP server | 包含一个简单的本地 MCP server 作为示例 | ✓ |
| 仅 tracing 验证，无 server | 不包含具体 MCP server | |

**User's choice:** 本地示例 MCP server
**Notes:** 无网络依赖，测试稳定

---

## Trace 事件格式与投递

| Option | Description | Selected |
|--------|-------------|----------|
| 混入 SSE 流 | 追踪事件作为新 SSE 事件类型混入聊天流 | |
| 单独 API 端点查询 | 通过 GET /traces/{run_id} 查询 | |
| 混合：SSE 通知 + API 查询 | 两种都做 | |

**User's choice:** 延后整个追踪功能
**Notes:** 用户决定先不考虑 trace 功能，未来会考虑用 OpenTelemetry 类似的 SDK 包来实现。CAP-05 和 CAP-01/02/03 中的"观察结构化事件"部分全部延后。

---

## Run 关联 ID 与追踪存储

**User's choice:** 随追踪一起延后
**Notes:** run_id 和追踪存储属于追踪基础设施的一部分，与 OpenTelemetry 集成一起实现。

---

## Scope Adjustment

Phase 4 scope was significantly revised during discussion:
- **Original scope:** CAP-01, CAP-02, CAP-03, CAP-05 (including structured tracing)
- **Revised scope:** Only tool/skill/MCP registration and end-to-end invocation
- **Deferred:** All tracing/observability → future phase with OpenTelemetry

## Claude's Discretion

- Exact example tool implementations
- Exact MCP server implementation
- Internal module layout
- How tools are declared in the framework
- Verification approach

## Deferred Ideas

- Structured call-chain tracing with OpenTelemetry — future phase
- Observing structured invocation/result/error events — future phase
- Run correlation ID — future phase
- Per-request dynamic tool registration — deferred
- Skill invocation (CAP-01 "skill") — researcher to clarify if skills differ from tools in agentscope-runtime
