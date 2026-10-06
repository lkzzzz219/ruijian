# Code Review Agent（代码审查 Agent）

一个大语言模型驱动的代码审查助手。它会自主读取代码、运行静态分析工具、结合 LLM 推理输出结构化的审查报告，支持多轮追问与修改建议。

## 功能特性

- **Agent 自主循环**：输入 → 推理 → 工具调用 → 观察 → 输出，最多 12 步自动收敛
- **4 个内置工具**：
  | 工具 | 作用 |
  |------|------|
  | `read_file` | 读取源代码文件（带行号、超长截断保护） |
  | `list_files` | 递归列出目录下的源代码文件 |
  | `analyze_code` | 基于 AST 的静态分析，检出 9 类常见缺陷 |
  | `syntax_check` | Python 语法检查，返回错误行号 |
- **静态分析规则**：可变默认参数、裸 except、吞异常、eval/exec 危险调用、global 滥用、未使用导入、函数过长、参数过多、缺少 docstring、硬编码密钥
- **上下文记忆**：多轮对话记忆，自动截断防止超出上下文窗口，支持 `/reset`
- **错误处理**：LLM 调用指数退避重试（区分可重试/不可重试错误）；工具异常转为文本反馈，不中断循环
- **结构化输出**：审查结论 + 质量评分（A/B/C/D）+ 按严重程度排序的问题清单 + 代码亮点

## 安装

```bash
pip install -r requirements.txt
```

## 配置

支持任意 OpenAI 兼容服务（Kimi/Moonshot、DeepSeek、OpenAI 等），通过环境变量配置：

```bash
# 必填：API Key（两个变量名任一即可）
export OPENAI_API_KEY="sk-xxx"
# 可选：API 地址与模型（默认使用 Kimi）
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
export MODEL_NAME="kimi-k2-0905-preview"
```

使用 DeepSeek 示例：

```bash
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export MODEL_NAME="deepseek-chat"
```

## 使用方法

### 1. 直接审查文件/目录

```bash
python main.py review examples/sample_buggy.py
python main.py review ./my_project
```

### 2. 交互模式

```bash
python main.py
```

```
review> examples/sample_buggy.py      # 审查文件
review> ```                            # 粘贴代码（以 ``` 结束）
review> 帮我修复第 5 行的问题           # 多轮追问
review> /reset                         # 清空上下文
review> /quit                          # 退出
```

### 3. 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## 运行示例

```text
$ python main.py review examples/sample_buggy.py
[step 1] 思考中...
[tool] read_file({"path": "examples/sample_buggy.py"})
[tool] analyze_code({"path": "examples/sample_buggy.py"})
[step 2] 思考中...

## 审查结论
代码存在多个高危缺陷，质量评分：D。

## 问题清单
- [高] sample_buggy.py:6 — 硬编码 API 密钥
  建议：改为 `os.environ["API_KEY"]` 读取环境变量
- [高] sample_buggy.py:9 — 可变默认参数 `cache=[]`
  建议：默认参数改为 None，函数体内初始化
- [高] sample_buggy.py:18 — 裸 except 吞掉所有异常
  建议：捕获具体异常并记录日志
...
```

## 项目结构

```
code-review-agent/
├── main.py                  # CLI 入口（单次审查 + 交互模式）
├── agent/
│   ├── core.py              # Agent 核心循环（ReAct 模式）
│   ├── llm.py               # OpenAI 兼容 API 客户端（重试、错误处理）
│   ├── memory.py            # 上下文记忆与截断
│   ├── prompts.py           # 系统提示词设计
│   └── tools/
│       ├── registry.py      # 工具注册表（schema + 统一异常处理）
│       ├── file_ops.py      # read_file / list_files
│       └── code_analysis.py # analyze_code / syntax_check（AST 分析）
├── examples/
│   └── sample_buggy.py      # 内置缺陷的演示代码
├── tests/
│   ├── test_tools.py        # 工具层测试
│   └── test_agent_loop.py   # Agent 循环测试（模拟 LLM）
├── requirements.txt
├── README.md
└── Design.md                # 设计文档
```

## 设计文档

架构设计、Prompt 设计思路与评审标准对照详见 [Design.md](Design.md)。
