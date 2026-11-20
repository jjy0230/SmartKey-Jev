# SmartKey-Jev 架构白皮书与技术深度研判

## 1. 架构总览 (System Architecture)

SmartKey-Jev 是一个常驻 Windows 桌面后台的亚毫秒级即时意图预测与动态快捷调度中枢。其目标是在用户双击快捷键（如连击两次 `Alt` 或 `Ctrl`）抬起的瞬间，捕获前台进程与屏幕划选文本，通过两级分桶启发式引擎与轻量决策模型收敛出 Top-3 候选宏动作，并在光标旁即时弹出极简悬浮卡片供用户盲按 `1 / 2 / 3` 触发执行。

若屏幕上无划选文本，双击快捷键将无缝切换为**居中极简 Spotlight 调度框**。

```
[用户双击快捷键抬起]
        │
        ├─▶ [屏幕有划选文本] ──▶ 捕获上下文 (Win32 + 双通道) ──▶ 两级分桶收敛 Top-3 ──▶ 鼠标旁悬浮卡片 (盲按 1/2/3)
        │                                                                             │
        │                                                                             ├─▶ 可编辑文本: 就地替换 (In-place Replace)
        │                                                                             ├─▶ 翻译/解释类: 展开侧边半透明抽屉
        │                                                                             └─▶ 搜索/外派类: 调浏览器/终端
        │
        └─▶ [屏幕无划选文本] ──▶ 屏幕正中央弹出极简居中搜索调度框 (Raycast / Spotlight 模式)
```

---

## 2. 核心技术壁垒与底层工程机制 (Deep Engineering Realities)

### 2.1 选中文本提取的“物理壁垒”与双通道解法
在 Windows 原生操作系统中，**不存在单一通用的 Win32 API 能够跨进程读取任意软件当前选中的文本**。业界通常面临以下两难抉择：
1. **UI Automation (UIA) 方案**：
   - *底层机制*：通过 `IUIAutomation::GetFocusedElement` 查询文本模式（`TextPattern` / `ValuePattern`）。
   - *优点*：纯内存调用，不破坏剪贴板，零副作用。
   - *致命缺陷*：主流软件（Electron、VS Code、Slack、Chrome、DirectX 游戏或自绘界面）对 UIA 的响应非常慢，单次跨进程 IPC 往往需要 30ms ~ 200ms，甚至会引发前台卡顿。
2. **合成按键注入 (Synthetic Ctrl+C) 方案**：
   - *底层机制*：备份剪贴板 ➔ 模拟按下 `Ctrl+C` ➔ 轮询等待前台窗口的 `WM_COPY` 响应 ➔ 读取剪贴板 ➔ 还原剪贴板。
   - *致命陷阱*：
     - **剪贴板污染**：Windows 10/11 的剪贴板历史记录（`Win+V`）以及第三方管理工具（Ditto）会截获这次合成的 `Ctrl+C`，导致用户历史记录里充斥着垃圾划词碎片。
     - **剪贴板独占锁竞争**：如果其他程序恰好正调用 `OpenClipboard(NULL)`，会导致访问冲突崩溃。
- **SmartKey-Jev 的工业级解法**：
  采用**双通道竞速 + 剪贴板隔离保护**：
  1. 优先尝试 UIA（设置 15ms 超时快速失败）；
  2. 若超时，立即启动带格式阻隔的合成 `Ctrl+C`：通过注册 Windows 特殊格式 `CanIncludeInClipboardHistory`（设为 0）和 `ExcludeClipboardContentFromMonitorProcessing`，向系统通知“禁止将此内容录入 Win+V 剪贴板历史记录”；
  3. 提取完毕后立即使用原序列化数据还原用户剪贴板，做到用户完全无感知。

### 2.2 双击 Alt 快捷键的状态机防死锁与菜单栏劫持
- **底层冲突**：
  在 Windows 标准规范中，`Alt` 键（`VK_MENU`）抬起时系统会自动激活当前窗口的菜单栏（Menu Loop 模态循环），抢占按键焦点。
  如果用户双击 Alt 后直接按数字键 `1`，系统会把 `1` 传递给菜单栏当做快捷键响应，导致悬浮卡片无法命中，同时前台应用界面发生乱跳。
- **SmartKey-Jev 的解法**：
  在 `WH_KEYBOARD_LL` 低级键盘钩子中实现滑动时间窗口状态机（默认 300ms 窗口）：
  1. 仅当在时间窗口内严格捕获到连续两次纯 Alt 抬起且中途没有其他键按下时，判定为触发；
  2. 触发瞬间，系统底层立即注入合成 `VK_ESCAPE` 或消费当前击键，提前终止当前前台窗口的系统菜单激活模态；
  3. 将窗口焦点无缝切换到常驻浮窗。

### 2.3 30ms 端到端延迟预算分解 (Latency Budget Breakdown)

| 阶段 | 传统方案耗时 | SmartKey-Jev 实测优化耗时 | 核心优化技术 |
| :--- | :--- | :--- | :--- |
| **热键与状态机检测** | 5~10ms | **< 0.5ms** | 原生 `WH_KEYBOARD_LL` 环形缓冲 |
| **进程元数据捕获** | 5~15ms | **< 0.3ms** | 原生 `QueryFullProcessImageNameW` |
| **选中文本提取** | 50~200ms | **5~25ms** | 双通道 + 剪贴板历史隔离快照 |
| **意图收敛打分** | 100~500ms (LLM) | **0.05~0.6ms** (规则) | **两级分桶 (Two-Tier Bucketing)** + 向量化正则 |
| **UI 悬浮渲染** | 50~150ms (冷启动) | **1~3ms** | **窗口池化预热 (Window Pooling)** |
| **端到端总延迟** | 200~800ms | **< 30ms** | 满足人类瞬时神经反馈感知 |

---

## 3. 智能三态交付与交互闭环

1. **A 类：就地直接替换 (In-place Replace)**
   - 包含动作：`format_json`、`polish_text`、`fix_code`
   - 机制：浮窗隐藏 ➔ 焦点回归前台 ➔ 写入隔离剪贴板 ➔ 模拟注入 `Ctrl+V`，原选区就地替换为处理结果。
2. **B 类：侧边半透明抽屉 (Drawer Panel)**
   - 包含动作：`translate`、`explain_code`、`summarize`、`dictionary`、`create_todo`
   - 机制：向右平滑滑出半透明 Markdown 抽屉卡片，结构化排版，支持一键复制与快捷 Esc 隐匿。
3. **C 类：系统外派 (External Dispatch)**
   - 包含动作：`open_url`、`search_web`、`terminal_cmd`、`regex_test`
   - 机制：浮窗即刻隐藏，直接调起系统默认浏览器或安全拉起终端。

---

## 4. 全屏游戏/视频安全豁免与多模式热键

- 支持 `double_alt`（默认）与 `double_ctrl` 双模式无缝切换；
- 原生探测前台窗口全屏状态（DirectX/Vulkan 独占全屏或全屏视频播放），游戏状态下钩子自动穿透，绝不弹窗打扰；
- 系统托盘提供微型图标，支持一键暂停/恢复常驻监听与热键模式切换。
