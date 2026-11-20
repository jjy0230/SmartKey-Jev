# SmartKey-Jev

> 桌面即时意图预测与动态快捷调度器 (Desktop Instant Intent Predictor & Dynamic Shortcut Dispatcher)

SmartKey-Jev 是一个常驻 Windows 桌面后台的高响应性效率中枢。
当用户在屏幕上划选文字并双击快捷键（默认双击 `Alt` 或 `Ctrl`）时，系统在毫秒级时延内捕获前台应用与文本上下文，通过“两级分桶启发式规则 + 决策模型接口”快速收敛出 Top-3 候选宏动作，并在鼠标旁唤出极简半透明悬浮卡片，支持用户盲打数字键 `1 / 2 / 3` 立即执行。

---

## 核心系统特性 (Enterprise Features)

1. **双通道上下文感知与 DPI 穿透**：
   - 优先调用 Win32 UI Automation，超时熔断降级为带系统隔离格式标志的合成 `Ctrl+C`（绝不污染 `Win+V` 剪贴板历史）。
   - 开启 `Per-Monitor V2` DPI 感知与物理工作区边缘钳位，副屏/多分辨率光标对齐误差 `< 2px`。
2. **两级分桶意图引擎 (Two-Tier Bucketing)**：
   - *Tier 1 (进程粗筛)*：根据 IDE、浏览器、社交沟通、办公套件、终端等前台类型将动作池从全量剪枝至 6~8 种。
   - *Tier 2 (特征细筛与概率收敛)*：通过 URL/JSON/堆栈/正则/时间实体等特征计算后验概率，耗时 `< 1ms`。
3. **智能三态交付与只读自适应降级**：
   - **A 类（就地替换）**：JSON 格式化、文本润色、代码报错修复。若检测到目标窗口只读或处于 UIPI 管理员特权隔离，**自动平滑降级为滑出侧边抽屉展示结果并写入剪贴板**，交互零盲区。
   - **B 类（侧边抽屉）**：即时翻译、代码解释、长文摘要、词典释义、日程提取，半透明 Markdown 排版，支持一键复制。
   - **C 类（系统外派）**：URL 直达、全局聚合搜索、Regex101、终端脚本拉起。
4. **未划词 Spotlight 居中调度**：
   - 屏幕上无文本划选时，双击快捷键无缝唤起**屏幕居中极简启动框**，支持键入关键词即时调度。
5. **全屏独占游戏/视频豁免**：
   - 检测到 DirectX/Vulkan 全屏游戏时，全局按键钩子自动静默穿透，绝不打扰游戏体验。
6. **开放插件生态 (Plugin SDK)**：
   - 内置时间戳转换（`convert_timestamp`）与 Base64 解码（`decode_base64`）插件，支持外部任意扩展。
7. **AnyJev 模型微调与端侧推理工具链**：
   - 内置指令数据集生成器（`dataset_generator.py`）、LoRA 微调脚本（`finetune_lora.py`）与 ONNX 嵌入式运行时接口。
8. **原生 Rust 内核原型 (`rust_core/`)**：
   - 包含面向未来的纯原生 Rust 实现，常驻内存 `< 8MB`，微秒级打分。

---

## 快速上手

### 依赖环境
- Windows 10 / 11
- Python 3.9+

```bash
pip install -r requirements.txt
```

### 1. 运行自动化测试与离线决策仿真
```bash
# 运行全量单元测试 (16 项)
python -m unittest discover tests

# 运行 6 大真实桌面场景时延基准测试
python demo_simulate.py
```

### 2. 启动常驻桌面守护服务
```bash
# 启动守护进程（默认双击 Alt 触发，托盘常驻）
python main.py

# 切换为双击 Ctrl 触发
python main.py --hotkey double_ctrl
```

### 3. 生成 AnyJev 微调数据集
```bash
python smartkey_jev/model/dataset_generator.py
```

---

## 目录结构

```text
SmartKey-Jev/
├── docs/
│   ├── ARCHITECTURE.md          # 详细架构与时延分解、底层机制研判
│   └── MODEL_INTERFACE.md       # Jev 模型接口规范与数据协议
├── rust_core/                   # 纯原生 Rust 内核原型 (<8MB 内存 / 微秒级)
│   ├── Cargo.toml
│   └── src/main.rs
├── smartkey_jev/
│   ├── core/                    # 数据模型与全局配置
│   ├── capture/                 # Win32 进程探测、DPI 穿透、全屏检测、双通道取词
│   ├── intent/                  # 两级分桶启发式引擎、模型接口与混合收敛器
│   ├── actions/                 # 12 种原子宏注册表、三态执行器、自定义宏加载
│   ├── ui/                      # 预热浮窗、侧边 Markdown 抽屉、Spotlight、原生托盘
│   ├── plugins/                 # 插件 SDK 规范与内置插件 (时间戳、Base64)
│   ├── model/                   # AnyJev 数据集生成、LoRA 微调与 ONNX 运行时
│   └── app.py                   # 守护进程主控制器
├── tests/                       # 全量单元测试套件
├── demo_simulate.py             # 离线推演与基准测试脚本
└── main.py                      # 主启动入口
```
