"""
Two-Tier Context Bucketing Engine.
Tier 1: Fast filtering by foreground process archetype (12 -> 6~8 candidates).
Tier 2: Heuristic feature extraction and posterior probability scoring.
"""

import math
import re
from typing import List, Dict, Set, Tuple
from ..core.models import SelectionContext, MacroAction, IntentPrediction, MacroCategory
from .base import BaseIntentPredictor


class ProcessArchetype:
    IDE = "ide"
    BROWSER = "browser"
    CHAT = "chat"
    OFFICE = "office"
    TERMINAL = "terminal"
    GENERAL = "general"


# Map executable names (lowercase) to process archetypes
PROCESS_MAPPING: Dict[str, str] = {
    # IDEs / Code Editors
    "code.exe": ProcessArchetype.IDE,
    "cursor.exe": ProcessArchetype.IDE,
    "idea64.exe": ProcessArchetype.IDE,
    "pycharm64.exe": ProcessArchetype.IDE,
    "clion64.exe": ProcessArchetype.IDE,
    "devenv.exe": ProcessArchetype.IDE,
    "sublime_text.exe": ProcessArchetype.IDE,
    "notepad++.exe": ProcessArchetype.IDE,

    # Browsers
    "chrome.exe": ProcessArchetype.BROWSER,
    "msedge.exe": ProcessArchetype.BROWSER,
    "firefox.exe": ProcessArchetype.BROWSER,
    "brave.exe": ProcessArchetype.BROWSER,
    "arc.exe": ProcessArchetype.BROWSER,

    # Instant Messaging & Collaboration
    "wechat.exe": ProcessArchetype.CHAT,
    "feishu.exe": ProcessArchetype.CHAT,
    "dingtalk.exe": ProcessArchetype.CHAT,
    "slack.exe": ProcessArchetype.CHAT,
    "telegram.exe": ProcessArchetype.CHAT,
    "discord.exe": ProcessArchetype.CHAT,
    "teams.exe": ProcessArchetype.CHAT,

    # Office & Note Taking
    "wps.exe": ProcessArchetype.OFFICE,
    "winword.exe": ProcessArchetype.OFFICE,
    "excel.exe": ProcessArchetype.OFFICE,
    "powerpnt.exe": ProcessArchetype.OFFICE,
    "notion.exe": ProcessArchetype.OFFICE,
    "obsidian.exe": ProcessArchetype.OFFICE,

    # Terminal / Consoles
    "windowsterminal.exe": ProcessArchetype.TERMINAL,
    "powershell.exe": ProcessArchetype.TERMINAL,
    "cmd.exe": ProcessArchetype.TERMINAL,
    "mintty.exe": ProcessArchetype.TERMINAL,
}

# Tier-1 Candidate Bucketing (Filter 12 -> 6~8 macros based on process archetype)
ARCHETYPE_PREFERRED_MACROS: Dict[str, List[str]] = {
    ProcessArchetype.IDE: [
        "fix_code", "explain_code", "format_json", "convert_case", "color_converter", "calculate", "open_path", "regex_test", "nlp_to_cmd", "search_web", "translate", "terminal_cmd", "make_qrcode", "pin_scratchpad"
    ],
    ProcessArchetype.BROWSER: [
        "translate", "summarize", "search_web", "open_url", "dictionary", "make_qrcode", "color_converter", "calculate", "open_path", "create_todo", "polish_text", "pin_scratchpad"
    ],
    ProcessArchetype.CHAT: [
        "polish_text", "translate", "calculate", "create_todo", "make_qrcode", "summarize", "search_web", "dictionary", "pin_scratchpad"
    ],
    ProcessArchetype.OFFICE: [
        "calculate", "polish_text", "summarize", "translate", "dictionary", "create_todo", "search_web", "make_qrcode", "pin_scratchpad"
    ],
    ProcessArchetype.TERMINAL: [
        "terminal_cmd", "nlp_to_cmd", "open_path", "calculate", "fix_code", "explain_code", "search_web", "translate", "format_json", "pin_scratchpad"
    ],
    ProcessArchetype.GENERAL: [
        "calculate", "open_path", "search_web", "translate", "make_qrcode", "summarize", "open_url", "dictionary", "create_todo", "polish_text", "color_converter", "pin_scratchpad"
    ],
}


class TwoTierRulePredictor(BaseIntentPredictor):
    """
    Two-tier Context Bucketing Predictor.
    Runs in < 1ms without requiring any local/remote neural network inference.
    Serves as the high-speed fallback and pre-filter for SmartKey-Jev.
    """

    # Compiled regex patterns for Tier-2 feature extraction
    URL_PATTERN = re.compile(r"^(https?://|www\.)[^\s/$.?#].[^\s]*$", re.IGNORECASE)
    JSON_PATTERN = re.compile(r"^\s*(\{[^}]*\}|\[[^\]]*\]|\"[^\"]+\"\s*:\s*.+)\s*$")
    EXCEPTION_PATTERN = re.compile(
        r"(Traceback \(most recent call last\)|Exception|Error:|at [a-zA-Z0-9_\.]+\([a-zA-Z0-9_\.]+:\d+\)|NullPointer|TypeError|SyntaxError|panic:)",
        re.IGNORECASE
    )
    CODE_KEYWORDS_PATTERN = re.compile(
        r"\b(def|class|function|const|let|var|public|private|static|return|import|export|fn|struct|impl|async|await)\b|(=>|::|->|===|!==)"
    )
    DATETIME_TODO_PATTERN = re.compile(
        r"(明天|后天|下周|截止|deadline|meeting|开会|同步|提醒我|\d{1,2}:\d{2}|\d{1,2}月\d{1,2}日|\b(pm|am|tomorrow|monday|friday)\b)",
        re.IGNORECASE
    )
    REGEX_SNIPPET_PATTERN = re.compile(r"(\^|\$|\\[dswb]|\[[a-zA-Z0-9\^]+\]|\(\?[:=!]|[\*\+\?]\?)")
    MATH_PATTERN = re.compile(r"^[\d\.\s\+\-\*\/\(\)\%\^\=]+$")
    PATH_PATTERN = re.compile(r"^([a-zA-Z]:[\\/]|/|~[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\<\>\:\"\|\\?\*]+$")
    CASE_PATTERN = re.compile(r'^[a-zA-Z0-9]+(_[a-zA-Z0-9]+)+$|^[a-z]+([A-Z][a-z0-9]+)+$')
    COLOR_PATTERN = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$|^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+', re.I)
    NLP_CMD_PATTERN = re.compile(r'(回退|撤销|commit|端口|\bport\b|杀进程|代码行数|\bdocker\b|\bnpm\b|\bgpu\b|显存)')

    def __init__(self):
        super().__init__()

    def get_process_archetype(self, process_name: str) -> str:
        proc = process_name.lower().strip()
        return PROCESS_MAPPING.get(proc, ProcessArchetype.GENERAL)

    def filter_tier1_candidates(
        self,
        archetype: str,
        candidates: List[MacroAction],
    ) -> List[MacroAction]:
        """Tier 1: Filter full macro candidate set to relevant subset (6-8 items)."""
        preferred_ids: Set[str] = set(ARCHETYPE_PREFERRED_MACROS.get(archetype, ARCHETYPE_PREFERRED_MACROS[ProcessArchetype.GENERAL]))
        filtered = [m for m in candidates if m.id in preferred_ids]
        # Guarantee at least some fallback candidates if registry has custom items
        if len(filtered) < 3:
            filtered = candidates[:8]
        return filtered

    def score_tier2_features(
        self,
        text: str,
        archetype: str,
        macro_id: str,
    ) -> Tuple[float, str]:
        """
        Tier 2: Calculate feature-based logits and attribution reason for a specific macro.
        Returns: (raw_logit, attribution_reason)
        """
        stripped = text.strip()
        length = len(stripped)
        is_single_word = len(stripped.split()) == 1 and length <= 25 and not any(c in stripped for c in "/\\{}[];:<>=+")
        has_cjk = any('\u4e00' <= char <= '\u9fff' for char in stripped)
        is_predominantly_latin = sum(1 for c in stripped if c.isascii() and c.isalpha()) > (length * 0.5)

        base_logit = 1.0
        reason = "Context affinity"

        # 0.01 Color Code pattern (e.g. "#4A90E2", "rgb(74, 144, 226)")
        if self.COLOR_PATTERN.match(stripped) and length <= 35:
            if macro_id == "color_converter":
                return 18.0, "HEX / RGB color code pattern detected"
            elif macro_id == "search_web":
                return 3.0, "Color code search"
            return 0.1, "Non-color action suppressed"

        # 0.02 Natural Language Command intent
        if self.NLP_CMD_PATTERN.search(stripped) and not any(c in stripped for c in "{};()=>") and length < 60:
            if macro_id == "nlp_to_cmd":
                return 16.0, "Natural language shell/git command intent"
            elif macro_id == "terminal_cmd":
                return 8.0, "Terminal execution candidate"

        # 0. Math Arithmetic Expression pattern (e.g. "1024 * 768", "(120 + 35) / 5")
        if self.MATH_PATTERN.match(stripped) and any(op in stripped for op in "+-*/%^") and any(c.isdigit() for c in stripped) and length < 50:
            if macro_id == "calculate":
                return 17.0, "Math arithmetic expression detected"
            elif macro_id == "search_web":
                return 4.0, "Math search"
            return 0.1, "Non-math action suppressed"

        # 1. URL pattern
        if self.URL_PATTERN.match(stripped):
            if macro_id == "open_url":
                return 15.0, "Exact URL pattern match"
            elif macro_id == "search_web":
                return 4.0, "URL query"
            return 0.1, "Non-URL action suppressed"

        # 0.1 Local File / Directory Path pattern (excluding web URLs)
        if not stripped.startswith("http://") and not stripped.startswith("https://") and (self.PATH_PATTERN.match(stripped) or ":\\" in stripped or (":/" in stripped and len(stripped) > 3 and stripped[1] == ':')) and length < 260 and not any(c in stripped for c in '<>"|?*'):
            if macro_id == "open_path":
                return 16.0, "Local file or directory path detected"
            elif macro_id == "terminal_cmd":
                return 6.0, "Path for terminal"

        # 0.2 Variable Identifier Case pattern (e.g. "user_profile_id", "getUserInfo")
        if self.CASE_PATTERN.match(stripped) and not any(c in stripped for c in " \t\n\r/\\{}[]();:"):
            if macro_id == "convert_case":
                return 16.0, "Variable naming identifier detected"
            elif macro_id in ("explain_code", "fix_code"):
                return 4.0, "Code token analysis"

        # 2. JSON / Key-Value detection (Fast heuristic + parser probe)
        is_json = False
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            import json
            try:
                json.loads(stripped)
                is_json = True
            except Exception:
                if '":' in stripped or "':" in stripped:
                    is_json = True

        if is_json:
            if macro_id == "format_json":
                return 16.0, "Valid JSON / Key-Value data structure"
            elif macro_id in ("explain_code", "fix_code"):
                return 4.0, "Data structure inspection"
            elif macro_id == "translate":
                return 0.1, "Data payload suppressed from translation"

        # 3. Stacktrace / Exception pattern
        if self.EXCEPTION_PATTERN.search(stripped):
            if macro_id == "fix_code":
                return 16.0, "Error stacktrace or exception detected"
            elif macro_id == "explain_code":
                return 8.0, "Exception analysis"
            elif macro_id == "search_web":
                return 5.0, "Search error trace"

        # 4. Code Syntax Keywords
        if self.CODE_KEYWORDS_PATTERN.search(stripped) or ("{" in stripped and "}" in stripped and ";" in stripped):
            if macro_id == "explain_code":
                return 12.0, "Code syntax keywords detected"
            elif macro_id == "fix_code":
                return 10.0, "Code snippet diagnosis"
            elif macro_id == "regex_test" and self.REGEX_SNIPPET_PATTERN.search(stripped):
                return 11.0, "Regular expression pattern syntax"

        # 5. Regex snippet standalone
        if self.REGEX_SNIPPET_PATTERN.search(stripped) and length < 60:
            if macro_id == "regex_test":
                return 13.0, "Regex token pattern detected"

        # 6. Todo / Schedule intent
        if self.DATETIME_TODO_PATTERN.search(stripped):
            if macro_id == "create_todo":
                return 12.0, "Temporal entity / schedule keyword detected"

        # 7. Single word lookup (Dictionary vs Translate)
        if is_single_word:
            if macro_id == "dictionary":
                return 12.0, "Single word token lookup"
            elif macro_id == "translate":
                return 9.0, "Word translation"
            elif macro_id == "search_web":
                return 6.0, "Keyword search"

        # 8. Translation & Summarization vs Text Length & Language
        if length > 50:
            if macro_id == "summarize":
                base_logit += 4.5
                reason = "Long text snippet suitable for summary"
            if macro_id == "polish_text" and has_cjk:
                base_logit += 3.5
                reason = "Chinese narrative refinement"

        if is_predominantly_latin and not has_cjk:
            if macro_id == "translate":
                base_logit += 5.0
                reason = "Foreign/Latin script detected, prioritize translation"

        # Process archetype bias
        if archetype == ProcessArchetype.IDE:
            if macro_id in ("fix_code", "explain_code", "format_json"):
                base_logit += 3.0
        elif archetype == ProcessArchetype.BROWSER:
            if macro_id in ("translate", "summarize", "search_web"):
                base_logit += 2.0
        elif archetype == ProcessArchetype.CHAT:
            if macro_id in ("polish_text", "translate", "create_todo"):
                base_logit += 2.5
        elif archetype == ProcessArchetype.TERMINAL:
            if macro_id in ("terminal_cmd", "fix_code", "search_web"):
                base_logit += 4.0

        return base_logit, reason

    def predict(
        self,
        context: SelectionContext,
        candidates: List[MacroAction],
        top_k: int = 3,
    ) -> List[IntentPrediction]:
        if not candidates:
            return []

        archetype = self.get_process_archetype(context.process_name)
        
        # Tier 1: Candidate bucketing
        tier1_candidates = self.filter_tier1_candidates(archetype, candidates)

        # Tier 2: Feature scoring
        scored: List[Tuple[MacroAction, float, str]] = []
        for macro in tier1_candidates:
            raw_logit, reason = self.score_tier2_features(context.text, archetype, macro.id)
            scored.append((macro, raw_logit, reason))

        # Softmax normalization for calibrated posterior probabilities
        max_logit = max(s[1] for s in scored)
        exp_sum = sum(math.exp(s[1] - max_logit) for s in scored)
        
        predictions: List[IntentPrediction] = []
        for macro, logit, reason in scored:
            prob = math.exp(logit - max_logit) / (exp_sum + 1e-9)
            predictions.append(
                IntentPrediction(
                    macro=macro,
                    confidence=round(prob, 4),
                    reason=f"[{archetype.upper()}] {reason}",
                    source="two_tier_rule",
                )
            )

        # Sort descending by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)

        # Assign rank (1, 2, 3...)
        for idx, pred in enumerate(predictions[:top_k], start=1):
            pred.rank = idx

        return predictions[:top_k]
