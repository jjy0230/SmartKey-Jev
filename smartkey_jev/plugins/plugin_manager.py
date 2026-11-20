"""
Plugin Manager.
Discovers, registers, and dispatches custom plugin actions.
"""

from typing import List, Dict, Optional
from .plugin_base import BasePlugin
from .builtin_timestamp import TimestampPlugin
from .builtin_base64 import Base64Plugin
from ..actions.registry import MacroRegistry, DEFAULT_REGISTRY
from ..core.models import SelectionContext, MacroAction


class PluginManager:
    """Manages extension plugins lifecycle and integrates with macro registry."""

    def __init__(self, registry: Optional[MacroRegistry] = None):
        self.registry = registry or DEFAULT_REGISTRY
        self._plugins: Dict[str, BasePlugin] = {}
        self._register_builtins()

    def _register_builtins(self):
        self.register_plugin(TimestampPlugin())
        self.register_plugin(Base64Plugin())

    def register_plugin(self, plugin: BasePlugin):
        """Registers a plugin instance and adds its action to the system registry."""
        self._plugins[plugin.id] = plugin
        macro = plugin.to_macro_action()
        self.registry.register(macro)

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[BasePlugin]:
        return list(self._plugins.values())

    def evaluate_plugin_matches(self, context: SelectionContext) -> List[tuple[MacroAction, float]]:
        """Evaluates affinity scores for all loaded plugins."""
        matches = []
        for plugin in self._plugins.values():
            score = plugin.match(context)
            if score > 0.1:
                matches.append((plugin.to_macro_action(), score))
        return matches


DEFAULT_PLUGIN_MANAGER = PluginManager()
