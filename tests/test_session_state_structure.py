"""Test: 对比 Memory-Only vs Full-Agent 的 session 结构（真实 LLM 调用）。

运行方式:
    cd /Users/chengtong/OpenSource/myagent
    .venv/bin/python -m pytest tests/test_session_state_structure.py -v -s

需要 .env 中配置了有效的 MODEL_NAME, MODEL_API_KEY, MODEL_BASE_URL。
"""

import asyncio
import json
import os
import tempfile

import pytest

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.session import JSONSession
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

# ---------------------------------------------------------------------------
# LLM 配置（从 .env 加载）
# ---------------------------------------------------------------------------

_SKIP_REASON = "需要 .env 中配置 MODEL_NAME, MODEL_API_KEY, MODEL_BASE_URL"


def _llm_available() -> bool:
    return all(os.environ.get(k) for k in ["MODEL_NAME", "MODEL_API_KEY", "MODEL_BASE_URL"])


def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()


def _get_model_config():
    return {
        "model_name": os.environ["MODEL_NAME"],
        "api_key": os.environ["MODEL_API_KEY"],
        "base_url": os.environ["MODEL_BASE_URL"],
    }


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------

async def get_weather(city: str) -> ToolResponse:
    """获取指定城市的天气信息。"""
    return ToolResponse(
        content=[TextBlock(type="text", text=f"{city}今天晴，气温22°C。")],
    )


async def calculate(expression: str) -> ToolResponse:
    """计算数学表达式的结果。"""
    try:
        result = eval(expression)  # noqa: S307
        return ToolResponse(
            content=[TextBlock(type="text", text=f"{expression} = {result}")],
        )
    except Exception as e:
        return ToolResponse(
            content=[TextBlock(type="text", text=f"计算错误: {e}")],
        )


# ---------------------------------------------------------------------------
# 构建真实的 ReActAgent（非流式，避免 thinking 模型流式超时）
# ---------------------------------------------------------------------------

def _build_agent(memory: InMemoryMemory | None = None) -> ReActAgent:
    config = _get_model_config()
    toolkit = Toolkit()
    toolkit.register_tool_function(get_weather)
    toolkit.register_tool_function(calculate)

    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=config["model_name"],
            api_key=config["api_key"],
            client_kwargs={"base_url": config["base_url"]},
            stream=False,
        ),
        sys_prompt="你是一个智能助手，可以查询天气和计算数学表达式。用中文回复，尽量简短。",
        formatter=OpenAIChatFormatter(),
        memory=memory or InMemoryMemory(),
        toolkit=toolkit,
    )
    agent.set_console_output_enabled(enabled=False)
    return agent


async def _chat(agent: ReActAgent, user_text: str) -> Msg:
    """发送消息并等待完整回复。"""
    return await agent.reply(Msg(name="user", content=user_text, role="user"))


def _print_summary(content):
    for i, item in enumerate(content):
        msg_dict, marks = item
        c = msg_dict.get("content")
        if isinstance(c, list):
            types = [b.get("type", "?") for b in c]
            tool_names = [b.get("name", "") for b in c if b.get("type") == "tool_use"]
            print(f"  [{i:2d}] {msg_dict['name']:12s} {msg_dict['role']:10s} {types}"
                  + (f" tool={tool_names}" if tool_names else ""))
        else:
            print(f"  [{i:2d}] {msg_dict['name']:12s} {msg_dict['role']:10s} \"{str(c)[:50]}\"")


# ---------------------------------------------------------------------------
# Test 1: 真实 LLM 对话（纯文本，无工具调用）
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _llm_available(), reason=_SKIP_REASON)
def test_memory_only_with_real_llm_text_only():
    """真实 LLM 对话（纯文本），查看 Memory-Only session 结构。"""
    memory = InMemoryMemory()
    agent = _build_agent(memory)

    reply = asyncio.run(_chat(agent, "你好，请用一句话介绍你自己。"))
    print(f"\nLLM 回复: {reply.get_text_content()}")

    state_dicts = {"memory": memory.state_dict()}
    output = json.dumps(state_dicts, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("【Memory-Only】纯文本对话 session 结构")
    print("=" * 60)
    print(output)
    print("=" * 60)

    parsed = json.loads(output)
    content = parsed["memory"]["content"]
    assert len(content) == 2

    print("\n消息摘要:")
    _print_summary(content)

    assert content[0][0]["role"] == "user"
    assert content[1][0]["role"] == "assistant"

    # 保存到 sessions/ 目录，方便查看实际文件
    session_dir = os.path.join(os.path.dirname(__file__), "..", "sessions")
    session = JSONSession(save_dir=session_dir)
    asyncio.run(session.save_session_state(
        session_id="test-real-text",
        memory=memory,
    ))
    session_file = os.path.join(session_dir, "test-real-text.json")
    print(f"\n📄 session 已保存到: {session_file} ({os.path.getsize(session_file)} bytes)")


# ---------------------------------------------------------------------------
# Test 2: 真实 LLM 对话（触发工具调用）
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _llm_available(), reason=_SKIP_REASON)
def test_memory_only_with_real_llm_tool_use():
    """真实 LLM 对话（触发工具调用），查看 tool_use/tool_result 存储结构。"""
    memory = InMemoryMemory()
    agent = _build_agent(memory)

    reply = asyncio.run(_chat(agent, "深圳今天天气怎么样？"))
    print(f"\nLLM 回复: {reply.get_text_content()}")

    state_dicts = {"memory": memory.state_dict()}
    output = json.dumps(state_dicts, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("【Memory-Only】工具调用 session 结构")
    print("=" * 60)
    print(output)
    print("=" * 60)

    parsed = json.loads(output)
    content = parsed["memory"]["content"]

    print(f"\n共 {len(content)} 条消息:")
    _print_summary(content)

    tool_use_msgs = [
        item[0] for item in content
        if isinstance(item[0].get("content"), list)
        and any(b.get("type") == "tool_use" for b in item[0]["content"])
    ]
    assert tool_use_msgs, "应该至少有一次工具调用"

    tool_use_block = next(
        b for b in tool_use_msgs[0]["content"] if b["type"] == "tool_use"
    )
    assert tool_use_block["name"] == "get_weather"
    print(f"\n✅ 工具调用: {tool_use_block['name']}({json.dumps(tool_use_block['input'], ensure_ascii=False)})")

    tool_result_msgs = [
        item[0] for item in content
        if isinstance(item[0].get("content"), list)
        and any(b.get("type") == "tool_result" for b in item[0]["content"])
    ]
    assert tool_result_msgs, "应该至少有一次工具结果"

    result_block = next(
        b for b in tool_result_msgs[0]["content"] if b["type"] == "tool_result"
    )
    assert result_block["id"] == tool_use_block["id"], "tool_result.id 应匹配 tool_use.id"
    print(f"✅ 工具结果: {result_block['output']}")

    # Memory-Only: 只保存 memory（项目当前做法）
    session_dir = os.path.join(os.path.dirname(__file__), "..", "sessions")
    session = JSONSession(save_dir=session_dir)
    asyncio.run(session.save_session_state(
        session_id="test-real-tool-use",
        memory=memory,
    ))
    session_file = os.path.join(session_dir, "test-real-tool-use.json")
    print(f"\n📄 Memory-Only session: {session_file} ({os.path.getsize(session_file)} bytes)")

    # Full-Agent: 同时保存 agent 和 memory
    asyncio.run(session.save_session_state(
        session_id="test-real-tool-use-full-agent",
        memory=memory,
        agent=agent,
    ))
    full_agent_file = os.path.join(session_dir, "test-real-tool-use-full-agent.json")
    print(f"📄 Full-Agent session: {full_agent_file} ({os.path.getsize(full_agent_file)} bytes)")


# ---------------------------------------------------------------------------
# Test 3: 多轮对话 + 对比 Full-Agent 结构
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _llm_available(), reason=_SKIP_REASON)
def test_multi_turn_compare_memory_only_vs_full_agent():
    """多轮对话后，对比 Memory-Only 和 Full-Agent 的 session 结构。"""
    memory = InMemoryMemory()
    agent = _build_agent(memory)

    print("\n--- 第1轮: 纯文本 ---")
    r1 = asyncio.run(_chat(agent, "你好，我叫小明。"))
    print(f"回复: {r1.get_text_content()}")

    print("--- 第2轮: 工具调用 ---")
    r2 = asyncio.run(_chat(agent, "帮我算一下 123 * 456 等于多少？"))
    print(f"回复: {r2.get_text_content()}")

    memory_only = {"memory": memory.state_dict()}
    full_agent = {
        "agent": {
            "name": agent.name,
            "_sys_prompt": agent._sys_prompt,
            "memory": memory.state_dict(),
        }
    }

    mem_only_json = json.dumps(memory_only, ensure_ascii=False, indent=2)
    full_agent_json = json.dumps(full_agent, ensure_ascii=False, indent=2)

    with tempfile.TemporaryDirectory() as tmpdir:
        mem_path = os.path.join(tmpdir, "memory_only.json")
        agent_path = os.path.join(tmpdir, "full_agent.json")

        with open(mem_path, "w") as f:
            f.write(mem_only_json)
        with open(agent_path, "w") as f:
            f.write(full_agent_json)

        mem_size = os.path.getsize(mem_path)
        agent_size = os.path.getsize(agent_path)

        print(f"\nMemory-Only:  {mem_size:>6} bytes")
        print(f"Full-Agent:   {agent_size:>6} bytes")
        print(f"差异:         {agent_size - mem_size:>6} bytes (多了 name + _sys_prompt)")

    content = memory_only["memory"]["content"]
    print(f"\n共 {len(content)} 条消息:")
    _print_summary(content)

    assert len(content) >= 4
    assert memory_only["memory"] == full_agent["agent"]["memory"]
    print("\n✅ Memory-Only 和 Full-Agent 中的 memory 内容完全一致")
    print("✅ 额外保存 name/_sys_prompt 是冗余的，构建 Agent 时重新注入即可")

    # 保存到 sessions/ 目录
    session_dir = os.path.join(os.path.dirname(__file__), "..", "sessions")
    session = JSONSession(save_dir=session_dir)
    asyncio.run(session.save_session_state(
        session_id="test-real-multi-turn",
        memory=memory,
    ))
    session_file = os.path.join(session_dir, "test-real-multi-turn.json")
    print(f"\n📄 session 已保存到: {session_file} ({os.path.getsize(session_file)} bytes)")
