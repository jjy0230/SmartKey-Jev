"""
System Macro Actions Registry.
Defines the 12 core atomic macro actions supported by SmartKey-Jev,
paired with their explicit smart delivery modes.
"""

from typing import Dict, List, Optional
from ..core.models import MacroAction, MacroCategory, MacroDeliveryMode


PRESET_MACROS: List[MacroAction] = [
    # ── B 类: 侧边半透明抽屉呈现 ──────────────────────────────────────
    MacroAction(
        id="translate",
        title="即时翻译",
        icon="🌐",
        category=MacroCategory.TRANSLATION,
        description="中英双向智能互译与语境对齐",
        delivery_mode=MacroDeliveryMode.DRAWER_PANEL,
        default_shortcut="1",
    ),
    MacroAction(
        id="explain_code",
        title="代码解释",
        icon="💡",
        category=MacroCategory.CODE,
        description="分析代码段控制流、算法复杂度与设计意图",
        delivery_mode=MacroDeliveryMode.DRAWER_PANEL,
        default_shortcut="3",
    ),
    MacroAction(
        id="summarize",
        title="要点总结",
        icon="📑",
        category=MacroCategory.WRITING,
        description="提炼长文、议题或聊天记录的核心 Bullet Points",
        delivery_mode=MacroDeliveryMode.DRAWER_PANEL,
        default_shortcut="1",
    ),
    MacroAction(
        id="dictionary",
        title="查词释义",
        icon="📖",
        category=MacroCategory.TRANSLATION,
        description="查询生词音标、词性及专业技术语境用例",
        delivery_mode=MacroDeliveryMode.DRAWER_PANEL,
        default_shortcut="2",
    ),
    MacroAction(
        id="create_todo",
        title="创建日程",
        icon="📅",
        category=MacroCategory.PRODUCTIVITY,
        description="自动提取选中文本中的截止时间与事项并加入待办",
        delivery_mode=MacroDeliveryMode.DRAWER_PANEL,
        default_shortcut="3",
    ),

    # ── A 类: 就地直接替换 ──────────────────────────────────────────
    MacroAction(
        id="format_json",
        title="格式化 JSON",
        icon="🧩",
        category=MacroCategory.UTILITY,
        description="校验并美化压缩的 JSON/字典结构并就地替换",
        delivery_mode=MacroDeliveryMode.IN_PLACE_REPLACE,
        default_shortcut="1",
    ),
    MacroAction(
        id="calculate",
        title="即时计算",
        icon="🧮",
        category=MacroCategory.UTILITY,
        description="计算选中的数学表达式并将算式就地替换为计算结果",
        delivery_mode=MacroDeliveryMode.IN_PLACE_REPLACE,
        default_shortcut="1",
    ),
    MacroAction(
        id="convert_case",
        title="命名转换",
        icon="🔤",
        category=MacroCategory.CODE,
        description="在 camelCase、snake_case、PascalCase 间快速切换",
        delivery_mode=MacroDeliveryMode.IN_PLACE_REPLACE,
        default_shortcut="2",
    ),
    MacroAction(
        id="polish_text",
        title="润色修辞",
        icon="✨",
        category=MacroCategory.WRITING,
        description="消除错别字、口语化表达，优化商务与学术语气",
        delivery_mode=MacroDeliveryMode.IN_PLACE_REPLACE,
        default_shortcut="3",
    ),
    MacroAction(
        id="fix_code",
        title="报错修复",
        icon="🛠️",
        category=MacroCategory.CODE,
        description="诊断选中的异常堆栈或代码 Bug 并就地替换修复",
        delivery_mode=MacroDeliveryMode.IN_PLACE_REPLACE,
        default_shortcut="2",
    ),

    # ── C 类: 外部系统外派 ──────────────────────────────────────────
    MacroAction(
        id="open_path",
        title="打开路径",
        icon="📂",
        category=MacroCategory.UTILITY,
        description="在 Windows 资源管理器中快速打开并定位选中的文件或目录",
        delivery_mode=MacroDeliveryMode.EXTERNAL_DISPATCH,
        default_shortcut="1",
    ),
    MacroAction(
        id="open_url",
        title="打开链接",
        icon="🔗",
        category=MacroCategory.UTILITY,
        description="直接在浏览器中安全访问提取到的 URL",
        delivery_mode=MacroDeliveryMode.EXTERNAL_DISPATCH,
        default_shortcut="1",
    ),
    MacroAction(
        id="search_web",
        title="网络搜索",
        icon="🔍",
        category=MacroCategory.SEARCH,
        description="使用默认浏览器在前沿搜索引擎检索选中文本",
        delivery_mode=MacroDeliveryMode.EXTERNAL_DISPATCH,
        default_shortcut="2",
    ),
    MacroAction(
        id="regex_test",
        title="正则解析",
        icon="🔍",
        category=MacroCategory.CODE,
        description="解析正则表达式并在 Regex101 中交互测试",
        delivery_mode=MacroDeliveryMode.EXTERNAL_DISPATCH,
        default_shortcut="2",
    ),
    MacroAction(
        id="terminal_cmd",
        title="终端运行",
        icon="💻",
        category=MacroCategory.UTILITY,
        description="解读并在系统终端安全执行选中的 Shell/PowerShell 脚本命令",
        delivery_mode=MacroDeliveryMode.EXTERNAL_DISPATCH,
        default_shortcut="3",
    ),
]


class MacroRegistry:
    """Central registry for discovering and querying macro actions."""

    def __init__(self, macros: Optional[List[MacroAction]] = None):
        self._macros: Dict[str, MacroAction] = {m.id: m for m in (macros or PRESET_MACROS)}

    def get(self, macro_id: str) -> Optional[MacroAction]:
        return self._macros.get(macro_id)

    def list_all(self) -> List[MacroAction]:
        return list(self._macros.values())

    def filter_by_category(self, category: MacroCategory) -> List[MacroAction]:
        return [m for m in self._macros.values() if m.category == category]

    def register(self, macro: MacroAction) -> None:
        self._macros[macro.id] = macro

    def unregister(self, macro_id: str) -> bool:
        if macro_id in self._macros:
            del self._macros[macro_id]
            return True
        return False


DEFAULT_REGISTRY = MacroRegistry()
