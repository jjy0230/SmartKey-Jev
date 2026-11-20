"""
Macro Action Executor.
Dispatches selected actions with the given context.
"""

import webbrowser
import urllib.parse
from typing import Dict, Any, Callable
from ..core.models import MacroAction, SelectionContext


class ActionExecutor:
    """Executes atomic macro actions against the captured desktop context."""

    def __init__(self):
        self._handlers: Dict[str, Callable[[SelectionContext, MacroAction], Dict[str, Any]]] = {
            "search_web": self._exec_search_web,
            "open_url": self._exec_open_url,
            "format_json": self._exec_format_json,
            "translate": self._exec_translate,
            "dictionary": self._exec_dictionary,
            "fix_code": self._exec_fix_code,
            "explain_code": self._exec_explain_code,
            "summarize": self._exec_summarize,
            "create_todo": self._exec_create_todo,
            "polish_text": self._exec_polish_text,
            "regex_test": self._exec_regex_test,
            "terminal_cmd": self._exec_terminal_cmd,
        }

    def execute(self, action: MacroAction, context: SelectionContext) -> Dict[str, Any]:
        """Dispatch execution to the registered handler."""
        handler = self._handlers.get(action.id, self._default_handler)
        return handler(context, action)

    def _exec_search_web(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        query = urllib.parse.quote(ctx.text.strip())
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return {"status": "success", "message": f"Opened search for: {ctx.text[:30]}..."}

    def _exec_open_url(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        url = ctx.text.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"status": "success", "message": f"Navigating to {url}"}

    def _exec_format_json(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        import json
        try:
            parsed = json.loads(ctx.text.strip())
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            return {"status": "success", "result": formatted}
        except Exception as e:
            return {"status": "error", "message": f"Invalid JSON: {str(e)}"}

    def _exec_translate(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        query = urllib.parse.quote(ctx.text.strip())
        url = f"https://translate.google.com/?text={query}"
        webbrowser.open(url)
        return {"status": "success", "message": "Dispatched translation request"}

    def _exec_dictionary(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        word = ctx.text.strip().split()[0] if ctx.text.strip() else ""
        url = f"https://www.youdao.com/result?word={urllib.parse.quote(word)}&lang=en"
        webbrowser.open(url)
        return {"status": "success", "message": f"Looked up word: {word}"}

    def _exec_fix_code(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {
            "status": "pending_model",
            "action": "fix_code",
            "prompt": f"Analyze and fix the following code or error:\n\n{ctx.text}",
        }

    def _exec_explain_code(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {
            "status": "pending_model",
            "action": "explain_code",
            "prompt": f"Explain the flow and complexity of this snippet:\n\n{ctx.text}",
        }

    def _exec_summarize(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {
            "status": "pending_model",
            "action": "summarize",
            "prompt": f"Summarize key insights:\n\n{ctx.text}",
        }

    def _exec_create_todo(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {
            "status": "pending_model",
            "action": "create_todo",
            "todo_item": ctx.text[:100],
        }

    def _exec_polish_text(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {
            "status": "pending_model",
            "action": "polish_text",
            "prompt": f"Polish and refine tone:\n\n{ctx.text}",
        }

    def _exec_regex_test(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        url = f"https://regex101.com/?regex={urllib.parse.quote(ctx.text.strip())}"
        webbrowser.open(url)
        return {"status": "success", "message": "Opened Regex101"}

    def _exec_terminal_cmd(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {"status": "info", "command": ctx.text.strip()}

    def _default_handler(self, ctx: SelectionContext, action: MacroAction) -> Dict[str, Any]:
        return {"status": "executed", "action_id": action.id, "text_preview": ctx.text[:50]}
