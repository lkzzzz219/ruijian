#!/usr/bin/env python3
"""代码审查 Agent —— 命令行入口。

用法：
    python main.py                     # 交互模式
    python main.py review <路径>       # 直接审查文件/目录
    python main.py --help
"""

from __future__ import annotations

import argparse
import os
import sys

from agent.core import Agent, console_event
from agent.llm import LLMClient, LLMError
from agent.prompts import HELP_TEXT, SYSTEM_PROMPT
from agent.tools.registry import ToolRegistry


def build_agent(verbose: bool = True) -> Agent:
    llm = LLMClient()
    tools = ToolRegistry()
    return Agent(
        llm=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        on_event=console_event if verbose else None,
    )


def read_multiline_code() -> str:
    """读取 ``` 包裹的多行代码输入。"""
    print("请粘贴代码，以单独一行 ``` 结束：")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "```":
            break
        lines.append(line)
    return "\n".join(lines)


def interactive(agent: Agent) -> None:
    print("代码审查 Agent 已启动。输入 /help 查看用法。\n")
    while True:
        try:
            user_input = input("review> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not user_input:
            continue
        if user_input in ("/quit", "/exit"):
            print("再见！")
            break
        if user_input == "/help":
            print(HELP_TEXT)
            continue
        if user_input == "/reset":
            agent.reset()
            print("上下文已清空。")
            continue
        if user_input.startswith("```"):
            code = read_multiline_code()
            if not code.strip():
                print("未收到代码。")
                continue
            user_input = f"请审查以下代码：\n```python\n{code}\n```"

        try:
            answer = agent.run(user_input)
        except LLMError as exc:
            print(f"\n[错误] {exc}", file=sys.stderr)
            continue
        print(f"\n{answer}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="代码审查 Agent")
    parser.add_argument("command", nargs="?", help="review / 直接输入文件路径")
    parser.add_argument("path", nargs="?", help="要审查的文件或目录")
    parser.add_argument("-q", "--quiet", action="store_true", help="不显示推理过程")
    args = parser.parse_args()

    try:
        agent = build_agent(verbose=not args.quiet)
    except LLMError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        sys.exit(1)

    target = args.path or (args.command if args.command != "review" else None)
    if target:
        if not os.path.exists(target):
            print(f"[错误] 路径不存在: {target}", file=sys.stderr)
            sys.exit(1)
        kind = "目录" if os.path.isdir(target) else "文件"
        try:
            answer = agent.run(f"请审查这个{kind}：{target}")
        except LLMError as exc:
            print(f"[错误] {exc}", file=sys.stderr)
            sys.exit(1)
        print(answer)
    else:
        interactive(agent)


if __name__ == "__main__":
    main()
