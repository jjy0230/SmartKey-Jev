"""
SmartKey-Jev Plugin SDK Base Interfaces.
Allows developers to build dynamic custom macro extensions with zero core modifications.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.models import SelectionContext, MacroCategory, MacroDeliveryMode, MacroAction


class BasePlugin(ABC):
    """Abstract base class for all SmartKey-Jev custom extension plugins."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier of the plugin action."""
        pass

    @property
    @abstractmethod
    def title(self) -> str:
        """Human-readable action title."""
        pass

    @property
    def icon(self) -> str:
        return "🧩"

    @property
    def category(self) -> MacroCategory:
        return MacroCategory.UTILITY

    @property
    def delivery_mode(self) -> MacroDeliveryMode:
        return MacroDeliveryMode.DRAWER_PANEL

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    def match(self, context: SelectionContext) -> float:
        """
        Calculates affinity score for the given context.
        Returns a float between 0.0 (no match) and 1.0 (exact match).
        """
        pass

    @abstractmethod
    def execute(self, context: SelectionContext) -> Dict[str, Any]:
        """Executes the plugin action against the selection context."""
        pass

    def to_macro_action(self) -> MacroAction:
        """Converts plugin instance to a standard MacroAction."""
        return MacroAction(
            id=self.id,
            title=self.title,
            icon=self.icon,
            category=self.category,
            description=self.description,
            delivery_mode=self.delivery_mode,
            metadata={"is_plugin": True, "plugin_instance": self},
        )
