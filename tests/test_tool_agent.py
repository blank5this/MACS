"""Tests for Tool Agent."""

import pytest

from macs_pkg.agents.tool_agent import ToolAgent, create_tool_agent_with_defaults
from macs_pkg.core.agent import AgentRole, Message


# ─────────────────────────────────────────────────────────────────────────────
# Mock provider for LLM-driven tool selection
# ─────────────────────────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, content):
        self.content = content
        self.model = "mock"
        self.usage = {"input_tokens": 1, "output_tokens": 1}
        self.tool_calls = []
        self.stop_reason = "stop"


class _SelectorProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    async def complete(self, messages, system=None, tools=None,
                       max_tokens=1024, temperature=0.7, **kwargs):
        self.calls += 1
        return _Resp(self.payload)

    def model_name(self):
        return "mock"


# ─────────────────────────────────────────────────────────────────────────────
# Initialization & registry
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_agent_init_defaults():
    a = ToolAgent(name="t1")
    assert a.name == "t1"
    assert a.role == AgentRole.TOOL
    assert a.list_tools() == []
    assert a._provider is None


def test_register_unregister_list():
    a = ToolAgent(name="t1")

    def my_tool(x):
        return x * 2

    a.register_tool("doubler", my_tool)
    assert "doubler" in a.list_tools()
    assert a.unregister_tool("doubler") is True
    assert a.list_tools() == []
    # second unregister returns False
    assert a.unregister_tool("doubler") is False


# ─────────────────────────────────────────────────────────────────────────────
# think() — request routing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_think_unknown_tool_reports_error():
    a = ToolAgent(name="t1")
    msg = Message(sender="x", receiver="t1",
                  content={"action": "execute_tool", "tool": "ghost"})
    resp = await a.think(msg)
    assert resp.content["action"] == "error"
    assert "ghost" in resp.content["error"]
    assert resp.content["available_tools"] == []


@pytest.mark.asyncio
async def test_think_valid_tool_returns_ready():
    a = ToolAgent(name="t1")
    a.register_tool("echo", lambda **kw: kw)

    msg = Message(sender="x", receiver="t1",
                  content={"action": "execute_tool", "tool": "echo",
                           "args": {"payload": "hi"}})
    resp = await a.think(msg)
    assert resp.content["action"] == "ready_to_execute"
    assert resp.content["tool"] == "echo"
    assert resp.content["args"] == {"payload": "hi"}


@pytest.mark.asyncio
async def test_think_list_tools():
    a = ToolAgent(name="t1")
    a.register_tool("a", lambda: 1)
    a.register_tool("b", lambda: 2)
    resp = await a.think(Message(content={"action": "list_tools"}))
    assert set(resp.content["tools"]) == {"a", "b"}


@pytest.mark.asyncio
async def test_think_describe_tool_with_docstring():
    a = ToolAgent(name="t1")

    def my_func(x):
        """Returns x squared."""
        return x * x

    a.register_tool("squarer", my_func)
    resp = await a.think(Message(content={"action": "describe_tool",
                                          "tool": "squarer"}))
    assert resp.content["description"] == "Returns x squared."


@pytest.mark.asyncio
async def test_think_describe_unknown_tool():
    a = ToolAgent(name="t1")
    resp = await a.think(Message(content={"action": "describe_tool",
                                          "tool": "missing"}))
    assert resp.content["action"] == "error"


@pytest.mark.asyncio
async def test_think_propose_and_vote():
    a = ToolAgent(name="t1")
    a.register_tool("hammer", lambda: "bang")

    propose = await a.think(Message(content={"action": "propose",
                                             "task": "hit a nail"}))
    assert propose.content["action"] == "propose"
    assert "hammer" in propose.content["proposal"]["available_tools"]

    vote_yes = await a.think(Message(
        content={"action": "vote", "proposal": {"confidence": 0.8}}))
    assert vote_yes.content["vote"] == "approve"
    vote_no = await a.think(Message(
        content={"action": "vote", "proposal": {"confidence": 0.2}}))
    assert vote_no.content["vote"] == "reject"


@pytest.mark.asyncio
async def test_think_unknown_action():
    a = ToolAgent(name="t1")
    resp = await a.think(Message(content={"action": "wat"}))
    assert resp.content["action"] == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# act() — tool execution
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_act_executes_sync_tool():
    a = ToolAgent(name="t1")
    a.register_tool("add", lambda x, y: x + y)

    msg = Message(sender="x", receiver="t1",
                  content={"action": "execute_tool", "tool": "add",
                           "args": {"x": 2, "y": 3}})
    response = await a.think(msg)
    outgoing = await a.act(response)
    assert len(outgoing) == 1
    result = outgoing[0].content
    assert result["success"] is True
    assert result["result"] == {"output": 5}


@pytest.mark.asyncio
async def test_act_executes_async_tool():
    a = ToolAgent(name="t1")

    async def async_tool(value):
        return {"computed": value * 10}

    a.register_tool("times_ten", async_tool)
    response = await a.think(Message(
        content={"action": "execute_tool", "tool": "times_ten",
                 "args": {"value": 4}}))
    outgoing = await a.act(response)
    assert outgoing[0].content["result"] == {"computed": 40}


@pytest.mark.asyncio
async def test_act_handles_tool_typeerror():
    a = ToolAgent(name="t1")
    a.register_tool("strict", lambda required_arg: required_arg)
    response = await a.think(Message(
        content={"action": "execute_tool", "tool": "strict",
                 "args": {"wrong": "name"}}))
    outgoing = await a.act(response)
    payload = outgoing[0].content
    assert payload["success"] is False
    assert "Invalid arguments" in payload["result"]["error"]


@pytest.mark.asyncio
async def test_act_handles_tool_runtime_exception():
    a = ToolAgent(name="t1")

    def boom(**_):
        raise RuntimeError("kaboom")

    a.register_tool("explode", boom)
    response = await a.think(Message(
        content={"action": "execute_tool", "tool": "explode", "args": {}}))
    outgoing = await a.act(response)
    payload = outgoing[0].content
    assert payload["success"] is False
    assert "kaboom" in payload["result"]["error"]


@pytest.mark.asyncio
async def test_execution_history_tracks_runs():
    a = ToolAgent(name="t1")
    a.register_tool("noop", lambda: "ok")
    for _ in range(3):
        resp = await a.think(Message(
            content={"action": "execute_tool", "tool": "noop", "args": {}}))
        await a.act(resp)

    history = a.get_execution_history()
    assert len(history) == 3
    assert all(h["success"] for h in history)
    assert a.get_execution_history(limit=1) == history[-1:]
    assert a.get_execution_history(tool_name="other") == []

    a.clear_history()
    assert a.get_execution_history() == []


# ─────────────────────────────────────────────────────────────────────────────
# ReactAgent lifecycle enforcement
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_act_before_think_raises():
    a = ToolAgent(name="t1")
    fake_response = Message(content={"action": "ready_to_execute",
                                     "tool": "x", "args": {}})
    with pytest.raises(RuntimeError, match="act.*called before think"):
        await a.act(fake_response)


# ─────────────────────────────────────────────────────────────────────────────
# LLM-driven tool selection
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_select_tool_returns_choice():
    provider = _SelectorProvider(
        '{"selected_tool": "search", "arguments": {"query": "python"}}'
    )
    a = ToolAgent(name="t1", provider=provider)
    a.register_tool("search", lambda query: {"hits": query})

    resp = await a.think(Message(content={
        "action": "execute_tool",
        "description": "look up something",
    }))
    assert provider.calls == 1
    assert resp.content["action"] == "ready_to_execute"
    assert resp.content["tool"] == "search"
    assert resp.content["args"]["query"] == "python"


@pytest.mark.asyncio
async def test_llm_select_falls_back_on_bad_json():
    """If LLM returns garbage, fall back to keyword matching."""
    provider = _SelectorProvider("not json at all")
    a = ToolAgent(name="t1", provider=provider)
    a.register_tool("search", lambda query: {"hits": query})

    resp = await a.think(Message(content={
        "action": "execute_tool",
        "description": "搜索 something",  # 中文关键词 → search
    }))
    # fallback picked the tool via keyword
    assert resp.content["action"] == "ready_to_execute"
    assert resp.content["tool"] == "search"


def test_fallback_tool_selection_chinese_keywords():
    a = ToolAgent(name="t1")
    a.register_tool("search", lambda: None)
    a.register_tool("calculator", lambda: None)
    a.register_tool("formatter", lambda: None)

    assert a._fallback_tool_selection("请搜索资料")[0] == "search"
    assert a._fallback_tool_selection("计算 1+1")[0] == "calculator"
    assert a._fallback_tool_selection("格式化输出")[0] == "formatter"


def test_fallback_tool_selection_no_tools_returns_unknown():
    a = ToolAgent(name="t1")
    assert a._fallback_tool_selection("anything")[0] == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# create_tool_agent_with_defaults — calculator safety regression test
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_default_calculator_does_arithmetic():
    a = create_tool_agent_with_defaults()
    calc = a._tool_registry["calculator"]
    assert (await calc("1 + 2 * 3"))["result"] == 7
    assert (await calc("2 ** 10"))["result"] == 1024
    assert (await calc("-5 + 3"))["result"] == -2


@pytest.mark.asyncio
async def test_default_calculator_rejects_arbitrary_code():
    """Regression guard: calculator must NOT execute arbitrary Python."""
    a = create_tool_agent_with_defaults()
    calc = a._tool_registry["calculator"]

    # None of these should succeed
    for hostile in [
        "__import__('os')",
        "open('x')",
        "exec('print(1)')",
        "lambda: 1",
        "(1).bit_length()",
    ]:
        result = await calc(hostile)
        assert "error" in result, f"hostile input must error: {hostile!r}"


@pytest.mark.asyncio
async def test_default_formatter():
    a = create_tool_agent_with_defaults()
    fmt = a._tool_registry["formatter"]
    out = await fmt({"a": 1}, "json")
    assert '"a": 1' in out["formatted"]


@pytest.mark.asyncio
async def test_default_search_placeholder():
    a = create_tool_agent_with_defaults()
    search = a._tool_registry["search"]
    out = await search("test query")
    assert out["query"] == "test query"
    assert out["results"] == []  # placeholder
