# SmartKey-Jev

> 桌面即时意图预测与动态快捷调度器 (Desktop Instant Intent Predictor & Dynamic Shortcut Dispatcher)

SmartKey-Jev 是一个常驻 Windows 桌面后台的高响应性效率中枢。
当用户在屏幕上划选文字并双击快捷键（默认双击 `Alt`）时，系统在毫秒级时延内捕获前台应用与文本上下文，通过“两级分桶启发式规则 + 决策模型接口”快速收敛出 Top-3 候选宏动作，并在鼠标旁唤出极简半透明悬浮卡片，支持用户盲打数字键 `1 / 2 / 3` 立即执行。

---

## 核心特性

- **双通道上下文提取**：优先调用 Win32 UI Automation，兜底使用隔离保护的合成 `Ctrl+C`（注入系统特殊格式阻隔标志，彻底避免污染 Windows `Win+V` 剪贴板历史）。
- **两级分桶意图引擎 (Two-Tier Bucketing)**：
  - *Tier 1 (进程粗筛)*：根据 IDE、浏览器、社交沟通、办公套件、终端等前台类型将动作池从 12 种预筛选至 6~8 种。
  - *Tier 2 (特征细筛与概率收敛)*：通过 URL/JSON/堆栈/正则/时间实体等特征计算后验概率，耗时 `< 1ms`。
- **模型接口已就绪**：解耦抽象 `BaseIntentPredictor` 与标准数据协议，内置 `MockJevModelClient` 与 `HttpJevModelClient`，保留对 AnyJev 与 4-bit 量化小模型（SmolLM2-1.7B / Qwen2.5-1.5B）的即插即用支持。
- **预热池化悬浮窗**：后台常驻预热无边框透明卡片，唤醒延迟 `< 3ms`，支持数字盲按与失焦自动隐藏。

---

## 快速上手

### 依赖环境
- Windows 10 / 11
- Python 3.9+

```bash
pip install -r requirements.txt
```

### 1. 运行离线决策仿真基准测试
```bash
python demo_simulate.py
```

### 2. 启动常驻后台守护服务
```bash
# 默认使用两级分桶规则引擎（双击 Alt 触发）
python main.py

# 启用模型接口测试桩（Mock AnyJev）
python main.py --enable-model --model-provider stub

# 连接本地/远程 AnyJev 模型端点
python main.py --enable-model --model-provider http --model-url http://127.0.0.1:8000/v1/intent
```

---

## 目录结构

```text
SmartKey-Jev/
├── docs/
│   ├── ARCHITECTURE.md          # 详细架构与时延分解、底层机制研判
│   └── MODEL_INTERFACE.md       # Jev 模型接口规范与数据协议
├── smartkey_jev/
│   ├── core/                    # 数据模型与全局配置
│   ├── capture/                 # Win32 进程探测、双通道文本提取、低级按键钩子
│   ├── intent/                  # 两级分桶启发式引擎、模型接口与混合收敛器
│   ├── actions/                 # 12 种原子宏注册表与执行器
│   ├── ui/                      # 毫秒级极简半透明悬浮卡片
│   └── app.py                   # 守护进程应用控制器
├── tests/                       # 单元测试套件
├── demo_simulate.py             # 离线推演与时延基准测试脚本
└── main.py                      # 主启动入口
```
