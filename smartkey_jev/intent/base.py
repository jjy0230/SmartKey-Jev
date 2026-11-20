"""
Abstract Base Classes for Intent Prediction.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..core.models import SelectionContext, MacroAction, IntentPrediction


class BaseIntentPredictor(ABC):
    """Abstract interface for predicting user intent from desktop selection context."""

    @abstractmethod
    def predict(
        self,
        context: SelectionContext,
        candidates: List[MacroAction],
        top_k: int = 3,
    ) -> List[IntentPrediction]:
        """
        Evaluate candidate macro actions against the active context.

        Args:
            context: Captured desktop context (process name, text snippet, cursor).
            candidates: Pool of candidate macro actions to rank.
            top_k: Number of highest-confidence predictions to return.

        Returns:
            Ranked list of IntentPrediction objects, sorted descending by confidence.
        """
        pass
