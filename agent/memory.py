"""对话记忆模块。

维护多轮对话的上下文消息列表，提供长度截断，防止超出模型上下文窗口。
"""

from __future__ import annotations

from typing import Any


class Memory:
    """基于消息列表的上下文记忆。

    保留 system 消息与最近若干条消息；截断时优先丢弃最早的中间消息，
    同时保证不会从 tool 消息处截断（避免 tool_call 孤儿消息）。
    """

    def __init__(self, system_prompt: str, max_messages: int = 40) -> None:
        self.max_messages = max_messages
        self._messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def add(self, role: str, content: str | None, **extra: Any) -> None:
        msg: dict[str, Any] = {"role": role, "content": content}
        msg.update(extra)
        self._messages.append(msg)
        self._truncate()

    def _truncate(self) -> None:
        if len(self._messages) <= self.max_messages:
            return
        overflow = len(self._messages) - self.max_messages
        # 保留 system 消息（索引 0），从索引 1 开始删除；跳过 tool 消息边界
        start = 1
        while overflow > 0 and start < len(self._messages):
            if self._messages[start].get("role") == "tool":
                start += 1
                continue
            del self._messages[start]
            overflow -= 1

    def clear(self) -> None:
        """清空历史，仅保留 system 消息。"""
        del self._messages[1:]
