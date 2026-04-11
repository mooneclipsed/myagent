# Phase 3: Request-Scoped Agent & Stateless Runtime - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 03-request-scoped-agent-stateless-runtime
**Areas discussed:** Agent 配置来源与格式, 验证与可观测性

---

## Agent 配置来源与格式

### Config 覆盖范围

| Option | Description | Selected |
|--------|-------------|----------|
| 最小可覆盖 | 只覆盖 model_name, api_key, base_url。sys_prompt 等固定。.env 作为 fallback。 | ✓ |
| 完整可配置 | 除了 model 配置，还可以覆盖 sys_prompt、formatter、agent 类型等。 | |
| 全量请求提供 | 请求必须提供全部 agent 配置，不依赖 .env fallback。 | |

**User's choice:** 最小可覆盖
**Notes:** 保持简单，Phase 3 只验证 config 可覆盖这一核心能力。

### 缺失字段处理

| Option | Description | Selected |
|--------|-------------|----------|
| 字段级 fallback | 每个字段独立 fallback 到 .env，可以只覆盖其中一个。 | ✓ |
| 全有或全无 | 要么全部从请求来，要么全部从 .env 来。 | |

**User's choice:** 字段级 fallback
**Notes:** 灵活性优先，允许部分覆盖。

### Config 在请求中的组织方式

| Option | Description | Selected |
|--------|-------------|----------|
| 顶层 agent_config | 在 messages 旁边加 agent_config 对象，向后兼容。 | ✓ |
| Header/QueryParam | 把 config 作为 header 或 query param 传入。 | |

**User's choice:** 顶层 agent_config
**Notes:** `{ "messages": [...], "agent_config": { "model_name": "..." } }` — 向后兼容，没有 agent_config 时用 .env。

---

## 验证与可观测性

### 验证方式

| Option | Description | Selected |
|--------|-------------|----------|
| pytest + smoke | 自动化测试 + smoke script，与 Phase 1/2 风格一致。 | ✓ |
| pytest + 响应可见 config | 在响应中返回实际使用的 config，方便 curl 调试。 | |

**User's choice:** pytest + smoke
**Notes:** 与已有验证模式一致。

### Stateless 验证粒度

| Option | Description | Selected |
|--------|-------------|----------|
| 实例隔离验证 | 只确保每个请求创建新 agent 实例，不共享内存。 | |
| 实例隔离 + config trace 日志 | 除了实例隔离，还加日志展示请求实际使用的配置值。 | ✓ |

**User's choice:** 实例隔离 + config trace 日志
**Notes:** 更有调试价值，可以直观看到 stateless 行为。

---

## Claude's Discretion

- Exact `agent_config` field names and pydantic model structure
- Exact logging format and level for config tracing
- Internal module layout for config resolution logic
- Exact test structure and smoke script shape

## Deferred Ideas

- Configurable `sys_prompt` per request — future phase
- Configurable agent type per request — future phase
- Configurable formatter per request — future phase
