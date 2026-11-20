"""
Hybrid Intent Convergence Engine.
Fuses Tier-1/Tier-2 rule predictions with optional neural model inference.
"""

from typing import List, Optional
from ..core.models import SelectionContext, MacroAction, IntentPrediction
from ..core.config import ModelConfig
from .base import BaseIntentPredictor
from .two_tier_rule import TwoTierRulePredictor
from .model_stub import JevModelPredictor, MockJevModelClient, HttpJevModelClient


class HybridIntentEngine(BaseIntentPredictor):
    """
    Unified intent convergence manager.
    Guarantees sub-millisecond fallback predictions via TwoTierRulePredictor,
    while seamlessly delegating to JevModelPredictor when active.
    """

    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        rule_predictor: Optional[TwoTierRulePredictor] = None,
        model_predictor: Optional[JevModelPredictor] = None,
    ):
        self.config = model_config or ModelConfig()
        self.rule_engine = rule_predictor or TwoTierRulePredictor()
        
        if model_predictor:
            self.model_engine = model_predictor
        else:
            if self.config.provider == "openai_compatible" or self.config.provider == "http":
                client = HttpJevModelClient(endpoint_url=self.config.endpoint_url)
            else:
                client = MockJevModelClient()
            self.model_engine = JevModelPredictor(client=client)

    def predict(
        self,
        context: SelectionContext,
        candidates: List[MacroAction],
        top_k: int = 3,
    ) -> List[IntentPrediction]:
        # Fast rule-based tier always computes baseline in <1ms
        rule_predictions = self.rule_engine.predict(context, candidates, top_k=top_k)

        # If model is not enabled, return rule predictions immediately
        if not self.config.enabled:
            return rule_predictions

        try:
            # Model inference pass
            model_predictions = self.model_engine.predict(context, candidates, top_k=top_k)
            if model_predictions:
                return model_predictions
        except Exception:
            # Graceful degradation to rule predictions
            pass

        return rule_predictions
