# SmartKey-Jev 模型接口与接入规范 (Model Interface Specification)

SmartKey-Jev 采用“接口先行、逻辑自闭环”的架构设计。即使本地尚未部署 4-bit 量化小模型，系统也能依赖「两级分桶启发式规则引擎」以亚毫秒级速度稳定跑通全链路。

当需要将 AnyJev 或本地微调模型（如 SmolLM2-1.7B、Qwen2.5-1.5B）接入系统时，只需实现标准协议即可。

---

## 1. 数据通信协议 (Data Contracts)

### 1.1 请求报文 (`ModelInferenceRequest`)

```json
{
  "process_name": "code.exe",
  "window_title": "app.py - SmartKey - Visual Studio Code",
  "selected_text": "Traceback (most recent call last):\n  File 'main.py', line 10\n    return val.strip()\nAttributeError: 'NoneType' object has no attribute 'strip'",
  "candidates": [
    {
      "id": "fix_code",
      "title": "报错修复",
      "category": "code",
      "description": "诊断选中的异常堆栈或代码 Bug 并给出修复方案"
    },
    {
      "id": "explain_code",
      "title": "代码解释",
      "category": "code",
      "description": "分析代码段控制流与设计意图"
    },
    {
      "id": "search_web",
      "title": "网络搜索",
      "category": "search",
      "description": "在前沿搜索引擎检索选中文本"
    }
  ],
  "max_tokens": 128,
  "temperature": 0.1
}
```

### 1.2 响应报文 (`ModelInferenceResponse`)

模型必须输出合法的 JSON 字符串（允许带 markdown 代码块标记）：

```json
{
  "predictions": [
    {
      "id": "fix_code",
      "probability": 0.88,
      "reason": "Python 异常堆栈 AttributeError 明确需要代码诊断"
    },
    {
      "id": "explain_code",
      "probability": 0.10,
      "reason": "上下文关联解释"
    },
    {
      "id": "search_web",
      "probability": 0.02,
      "reason": "通用搜索兜底"
    }
  ]
}
```

---

## 2. 推荐 Prompt 模板 (Small Language Model Optimized)

专为 1.5B~2B 参数级别小模型设计的高信噪比 Prompt 模板：

```text
<|im_start|>system
You are SmartKey-Jev, a desktop intent classification head. Given the active application and the user's selected text snippet, predict the top 3 most relevant macro actions and output calibrated posterior probabilities.
Respond ONLY with a JSON object in the format:
{"predictions": [{"id": "<macro_id>", "probability": 0.85, "reason": "why"}]}
<|im_end|>
<|im_start|>user
[Desktop Context]
Process: {process_name}
Window: {window_title}
Selected Snippet (Max 300 chars):
"""
{selected_text}
"""

[Candidate Pool ({candidate_count} actions)]:
{candidate_lines}

Predict the top 3 optimal actions:
<|im_end|>
<|im_start|>assistant
```

---

## 3. 本地与远程接入指引

### 3.1 启用方式
在启动应用时传入参数即可无缝切换模型源：

```bash
# 1. 采用内置 Mock 桩（验证逻辑与流水线）
python main.py --enable-model --model-provider stub

# 2. 接入本地部署的 Ollama / vLLM / llama.cpp 服务
python main.py --enable-model --model-provider http --model-url http://127.0.0.1:8000/v1/intent
```

### 3.2 自定义 Client 扩展
继承 `BaseModelClient` 并注入 `HybridIntentEngine`：

```python
from smartkey_jev.intent.model_stub import BaseModelClient
from smartkey_jev.intent.model_interface import ModelInferenceRequest, ModelInferenceResponse

class MyAnyJevClient(BaseModelClient):
    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResponse:
        # 调用你的 C++/Rust 本地推理动态链接库或专用管道
        ...
```
