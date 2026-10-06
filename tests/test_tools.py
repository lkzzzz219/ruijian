"""工具层单元测试：不依赖 LLM，可直接运行。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.code_analysis import analyze_code, syntax_check
from agent.tools.file_ops import list_files, read_file
from agent.tools.registry import ToolRegistry

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "sample_buggy.py")


def test_analyze_sample_finds_planted_bugs():
    result = json.loads(analyze_code(path=SAMPLE))
    rules = {i["rule"] for i in result["issues"]}
    assert "mutable-default-arg" in rules, "应检出可变默认参数"
    assert "bare-except" in rules, "应检出裸 except"
    assert "eval-exec-usage" in rules, "应检出 eval 使用"
    assert "hardcoded-secret" in rules, "应检出硬编码密钥"
    assert "too-many-args" in rules, "应检出参数过多"
    assert "unused-import" in rules, "应检出未使用导入"
    assert result["issue_count"] >= 6


def test_analyze_inline_code():
    code = "def f(x=[]):\n    return x\n"
    result = json.loads(analyze_code(code=code))
    assert any(i["rule"] == "mutable-default-arg" for i in result["issues"])


def test_syntax_check_ok_and_error():
    ok = json.loads(syntax_check(code="x = 1"))
    assert ok["ok"] is True
    bad = json.loads(syntax_check(code="def f(:\n"))
    assert bad["ok"] is False and bad["line"] == 1


def test_read_file_with_line_numbers():
    result = json.loads(read_file(SAMPLE))
    assert "content" in result and "1 | " in result["content"]


def test_read_file_missing():
    result = json.loads(read_file("/nonexistent/x.py"))
    assert "error" in result


def test_list_files():
    result = json.loads(list_files(os.path.dirname(SAMPLE)))
    assert "sample_buggy.py" in result["files"]


def test_registry_executes_and_catches_errors():
    reg = ToolRegistry()
    assert set(reg.names) == {"read_file", "list_files", "analyze_code", "syntax_check"}
    # 正常调用
    out = json.loads(reg.execute("syntax_check", {"code": "x = 1"}))
    assert out["ok"] is True
    # 未知工具不抛异常
    out = json.loads(reg.execute("no_such_tool", {}))
    assert "error" in out
    # 参数错误不抛异常
    out = json.loads(reg.execute("read_file", {}))
    assert "error" in out
