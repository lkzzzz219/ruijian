"""工具注册表。

集中管理工具的 JSON Schema（供 LLM Function Calling）与执行入口，
统一异常处理，任何工具错误都转为文本返回给模型而不是中断循环。
"""

from __future__ import annotations

import json
import traceback
from typing import Any, Callable

from . import code_analysis, file_ops


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._register_defaults()

    def register(self, name: str, description: str, parameters: dict[str, Any], func: Callable[..., str]) -> None:
        self._tools[name] = {
            "schema": {
                "type": "function",
                "function": {"name": name, "description": description, "parameters": parameters},
            },
            "func": func,
        }

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [t["schema"] for t in self._tools.values()]

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"未知工具: {name}，可用工具: {self.names}"}, ensure_ascii=False)
        try:
            return tool["func"](**arguments)
        except TypeError as exc:
            return json.dumps({"error": f"参数错误: {exc}"}, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001 - 工具异常不应中断 Agent 循环
            return json.dumps(
                {"error": f"工具执行失败: {exc}", "trace": traceback.format_exc(limit=3)},
                ensure_ascii=False,
            )

    def _register_defaults(self) -> None:
        self.register(
            "read_file",
            "读取指定源代码文件的完整内容（带行号），用于审查代码。文件过大时返回前 400 行。",
            {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "源代码文件路径"}},
                "required": ["path"],
            },
            file_ops.read_file,
        )
        self.register(
            "list_files",
            "列出目录下的源代码文件（递归），用于了解项目结构。",
            {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "目录路径"},
                    "max_files": {"type": "integer", "description": "最多返回的文件数，默认 50"},
                },
                "required": ["directory"],
            },
            file_ops.list_files,
        )
        self.register(
            "analyze_code",
            "对 Python 代码做 AST 静态分析，检测常见缺陷：可变默认参数、裸 except、eval/exec、"
            "未使用导入、过长函数、过多参数、缺少文档字符串、硬编码密码等。返回带行号的问题列表。",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Python 文件路径（与 code 二选一）"},
                    "code": {"type": "string", "description": "直接传入的代码字符串（与 path 二选一）"},
                },
            },
            code_analysis.analyze_code,
        )
        self.register(
            "syntax_check",
            "检查 Python 代码是否存在语法错误，返回错误行号与信息。",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Python 文件路径（与 code 二选一）"},
                    "code": {"type": "string", "description": "直接传入的代码字符串（与 path 二选一）"},
                },
            },
            code_analysis.syntax_check,
        )
