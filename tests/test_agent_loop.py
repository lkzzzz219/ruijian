"""Agent 循环测试：用模拟 LLM 验证 推理 → 工具调用 → 输出 的完整链路。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import Agent
from agent.llm import LLMResponse, ToolCall
from agent.prompts import SYSTEM_PROMPT
from agent.tools.registry import ToolRegistry


class FakeLLM:
    """模拟 LLM：第一轮请求调用工具，第二轮根据工具结果给出最终答复。"""

    def __init__(self):
        self.rounds = 0
        self.seen_tool_result = None

    def chat(self, messages, tools=None):
        assert tools, "Agent 应传入工具 schema"
        self.rounds += 1
        # 检查是否已收到工具结果
        for m in messages:
            if m.get("role") == "tool":
                self.seen_tool_result = m["content"]
        if self.rounds == 1:
            return LLMResponse(
                content=None,
                tool_calls=[ToolCall(id="call_1", name="syntax_check", arguments={"code": "x = 1"})],
            )
        return LLMResponse(content="代码语法正确，评分 A。", tool_calls=[])


class LoopingLLM:
    """不停要求调用工具的 LLM，用于验证 max_steps 保护。"""

    def chat(self, messages, tools=None):
        return LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="c", name="syntax_check", arguments={"code": "x=1"})],
        )


def test_agent_full_loop():
    agent = Agent(llm=FakeLLM(), tools=ToolRegistry(), system_prompt=SYSTEM_PROMPT)
    answer = agent.run("请检查 x = 1 的语法")
    assert answer == "代码语法正确，评分 A。"
    # 工具结果确实回到了对话上下文
    assert agent.llm.seen_tool_result is not None
    assert json.loads(agent.llm.seen_tool_result)["ok"] is True
    # 消息序列完整：system, user, assistant(tool_calls), tool, assistant
    roles = [m["role"] for m in agent.memory.messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]


def test_agent_max_steps_protection():
    agent = Agent(llm=LoopingLLM(), tools=ToolRegistry(), system_prompt=SYSTEM_PROMPT, max_steps=3)
    answer = agent.run("测试")
    assert "最大推理步数" in answer


def test_agent_memory_reset():
    agent = Agent(llm=FakeLLM(), tools=ToolRegistry(), system_prompt=SYSTEM_PROMPT)
    agent.run("第一条消息")
    agent.reset()
    roles = [m["role"] for m in agent.memory.messages]
    assert roles == ["system"]
