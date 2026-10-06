"""Agent 核心循环。

实现经典的 ReAct 模式：输入 → 推理 → 工具调用 → 观察 → 输出，
循环执行直到模型给出最终答复或达到最大步数。
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Protocol

from .llm import LLMResponse
from .memory import Memory
from .tools.registry import ToolRegistry


class ChatModel(Protocol):
    """LLM 客户端协议，便于测试时替换为模拟实现。"""

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse: ...


class Agent:
    """代码审查 Agent。

    Args:
        llm:          LLM 客户端（满足 ChatModel 协议）
        tools:        工具注册表
        system_prompt: 系统提示词
        max_steps:    单次任务的最大 推理-工具 循环步数，防止死循环
        on_event:     事件回调（用于 CLI 展示推理过程），签名为 (事件名, 数据)
    """

    def __init__(
        self,
        llm: ChatModel,
        tools: ToolRegistry,
        system_prompt: str,
        max_steps: int = 12,
        on_event: Callable[[str, Any], None] | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.memory = Memory(system_prompt)
        self._on_event = on_event or (lambda name, data: None)

    def run(self, user_input: str) -> str:
        """处理一轮用户输入，返回最终文本答复。"""
        self.memory.add("user", user_input)

        for step in range(1, self.max_steps + 1):
            self._on_event("thinking", step)
            response = self.llm.chat(self.memory.messages, tools=self.tools.schemas)

            if not response.has_tool_calls:
                answer = response.content or ""
                self.memory.add("assistant", answer)
                self._on_event("answer", answer)
                return answer

            # 记录 assistant 的工具调用请求，保持消息序列完整
            self.memory.add(
                "assistant",
                response.content,
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)},
                    }
                    for tc in response.tool_calls
                ],
            )

            for call in response.tool_calls:
                self._on_event("tool_call", call)
                result = self.tools.execute(call.name, call.arguments)
                self._on_event("tool_result", {"name": call.name, "result": result})
                self.memory.add("tool", result, tool_call_id=call.id, name=call.name)

        fallback = f"已达到最大推理步数（{self.max_steps}），请缩小审查范围后重试。"
        self.memory.add("assistant", fallback)
        return fallback

    def reset(self) -> None:
        """清空对话记忆，开始新会话。"""
        self.memory.clear()


def console_event(name: str, data: Any) -> None:
    """默认的 CLI 事件展示：向 stderr 打印推理过程，不污染最终输出。"""
    if name == "thinking":
        print(f"\033[2m[step {data}] 思考中...\033[0m", file=sys.stderr)
    elif name == "tool_call":
        args = json.dumps(data.arguments, ensure_ascii=False)
        if len(args) > 120:
            args = args[:120] + "..."
        print(f"\033[36m[tool] {data.name}({args})\033[0m", file=sys.stderr)
    elif name == "tool_result":
        text = str(data["result"])
        if len(text) > 200:
            text = text[:200] + "..."
        print(f"\033[2m[result] {text}\033[0m", file=sys.stderr)
