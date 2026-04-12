# Phase 8: Parity & Demo Flows - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 08-parity-demo-flows
**Areas discussed:** Skill 定义与分类, Demo Flow 形式, Parity 验证范围, 文档放置与结构

---

## Skill 定义与分类

| Option | Description | Selected |
|--------|-------------|----------|
| Skill = Tool（不区分） | agentscope-runtime 不区分 skill 和 tool，将现有 tool 示例直接作为 skill 示例覆盖 | |
| 文档上人为区分 | 将某些 tool 定义为 'skill'，文档上标注 | |
| 重新调研框架 skill 支持 | 调研 agentscope-runtime 是否有独立的 skill 机制（pipeline、workflow 等） | ✓ |

**User's choice:** 重新调研框架 skill 支持
**Notes:** 需在研究阶段确认 agentscope-runtime 是否有独立于 tool 的 skill 注册机制。如果有则创建单独示例，如果没有则回退到 skill = tool 并在文档中注明。

---

## Demo Flow 形式

### Q1: 端到端 demo 流程的呈现形式

| Option | Description | Selected |
|--------|-------------|----------|
| Shell 脚本 | 自包含 .sh 脚本，一键启动服务 + 发送请求 + 显示结果 | |
| Markdown + curl 命令 | 文档中嵌入 curl 命令，用户手动执行 | |
| Python 自动化脚本 | 用 httpx 发送请求，自动化验证响应内容 | ✓ |
| Jupyter notebook | 交互式 notebook，逐步执行 | |

**User's choice:** Python 自动化脚本

### Q2: 脚本组织方式

| Option | Description | Selected |
|--------|-------------|----------|
| 每能力独立脚本 | demo_tool.py, demo_mcp.py, demo_resume.py, demo_skill.py | ✓ |
| 统一入口 + 参数 | python demo.py --capability tool | |
| 全部顺序执行 | 一个脚本跑完所有 demo | |

**User's choice:** 每能力独立脚本

### Q3: 是否包含自动化断言

| Option | Description | Selected |
|--------|-------------|----------|
| 内置断言 | assert 失败时退出码非零，适合 CI | ✓ |
| 纯展示（无断言） | 只打印请求和响应 | |
| 打印 + 断言 | 两者都做 | |

**User's choice:** 内置断言

### Q4: 脚本放置位置

| Option | Description | Selected |
|--------|-------------|----------|
| scripts/demos/ + uv run | 独立目录，通过 uv run 运行，依赖 httpx | ✓ |
| tests/demos/ + pytest | 复用 pytest 基础设施 | |

**User's choice:** scripts/demos/ + uv run

---

## Parity 验证范围

### Q1: Parity 验证标准

| Option | Description | Selected |
|--------|-------------|----------|
| 对话内容一致性 | 相同 session 数据 → JSON/Redis resume 后产生相同对话结果 | ✓ |
| 各自能工作即可 | 只验证两个后端都能正常 resume | |
| 全面行为对比 | 对话内容 + API 响应结构 + 错误处理 + 边界情况 | |

**User's choice:** 对话内容一致性

### Q2: Parity 实现方式

| Option | Description | Selected |
|--------|-------------|----------|
| pytest 测试 | 自动化测试，先 JSON 后 Redis，断言一致 | ✓ |
| demo 脚本 | 手动运行对比 | |
| pytest + demo 都要 | 两者都做 | |

**User's choice:** pytest 测试

### Q3: Redis 环境处理

| Option | Description | Selected |
|--------|-------------|----------|
| fakeredis 模拟 | 无需真实 Redis，CI 零依赖 | ✓ |
| 真实 Redis | 需要运行 Redis 实例 | |
| fakeredis 默认 + 可选真实 Redis | 通过环境变量切换 | |

**User's choice:** fakeredis 模拟

---

## 文档放置与结构

### Q1: 文档放置位置

| Option | Description | Selected |
|--------|-------------|----------|
| README.md 统一指南 | 一个文件包含启动 + demo 命令 + 预期输出 | ✓ |
| docs/ 目录拆分 | getting-started.md, demo-tool.md 等 | |
| 脚本内联文档 | 每个 demo 脚本头部包含完整用法文档 | |

**User's choice:** README.md 统一指南

### Q2: README 内容范围

| Option | Description | Selected |
|--------|-------------|----------|
| 精简指南 | 启动 + 命令 + 预期输出 | ✓ |
| 完整文档 | 架构 + API + troubleshooting | |

**User's choice:** 精简指南（启动 + 命令 + 预期输出）

---

## Claude's Discretion

- Exact pytest test structure for parity validation
- README formatting and section organization
- Whether demo scripts need a shared helper module
- Internal structure of each demo script
- How demo scripts handle the prerequisite of a running service

## Deferred Ideas

No scope creep — discussion stayed within phase boundaries.
