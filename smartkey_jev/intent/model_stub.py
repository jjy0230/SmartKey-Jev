"""
Model Interface Stub & Pluggable Clients.
Leaves clean abstraction hooks for AnyJev, local GGUF/llama.cpp, or remote HTTP endpoints.
"""

import time
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from ..core.models import SelectionContext, MacroAction, IntentPrediction
from .base import BaseIntentPredictor
from .model_interface import (
    ModelInferenceRequest,
    ModelInferenceResponse,
    ModelCandidateInput,
    ModelMacroScore,
)


class BaseModelClient(ABC):
    """Abstract client interface for interacting with Jev intent models."""

    @abstractmethod
    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResponse:
        pass


class MockJevModelClient(BaseModelClient):
    """
    Mock inference client that simulates AnyJev 4-bit SLM behavior.
    Allows zero-deployment testing of the model scoring logic and pipeline integration.
    """

    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResponse:
        start_t = time.time()
        text_lower = request.selected_text.lower()
        proc_lower = request.process_name.lower()

        scores: List[ModelMacroScore] = []

        # Synthetic posterior probability calculation simulating fine-tuned weights
        for cand in request.candidates:
            cid = cand.id
            prob = 0.05
            reason = "Base prior"

            if ("code" in proc_lower or "cursor" in proc_lower) and cid in ("fix_code", "explain_code"):
                prob = 0.88 if "error" in text_lower or "traceback" in text_lower else 0.72
                reason = "IDE context detected with code pattern"
            elif cid == "open_url" and ("http://" in text_lower or "https://" in text_lower or "www." in text_lower):
                prob = 0.96
                reason = "URL pattern identified"
            elif cid == "format_json" and ("{" in text_lower or "[" in text_lower):
                prob = 0.91
                reason = "JSON structure identified"
            elif cid == "create_todo" and any(k in text_lower for k in ["deadline", "tomorrow", "明天", "开会", "提醒"]):
                prob = 0.89
                reason = "Calendar/schedule keyword extracted"
            elif cid == "translate" and not any('\u4e00' <= char <= '\u9fff' for char in request.selected_text):
                prob = 0.85
                reason = "Foreign language text detected"
            elif cid == "summarize" and len(request.selected_text) > 80:
                prob = 0.82
                reason = "Long text passage detected"
            elif cid == "dictionary" and len(request.selected_text.split()) == 1:
                prob = 0.93
                reason = "Single vocabulary term detected"

            scores.append(ModelMacroScore(id=cid, probability=prob, reason=reason))

        # Normalize probabilities with Softmax-like temperature
        max_p = max((s.probability for s in scores), default=0.1)
        exp_sum = sum(math.exp((s.probability - max_p) * 2.0) for s in scores)
        normalized_scores = [
            ModelMacroScore(
                id=s.id,
                probability=round(math.exp((s.probability - max_p) * 2.0) / (exp_sum + 1e-9), 4),
                reason=s.reason,
            )
            for s in scores
        ]

        normalized_scores.sort(key=lambda s: s.probability, reverse=True)
        latency_ms = (time.time() - start_t) * 1000.0

        return ModelInferenceResponse(
            predictions=normalized_scores,
            raw_response="[Mock AnyJev Inference]",
            latency_ms=round(latency_ms, 2),
        )


class HttpJevModelClient(BaseModelClient):
    """
    HTTP client for connecting to an AnyJev server, vLLM, or Ollama instance.
    Ready for deployment when local weights or a model server become available.
    """

    def __init__(self, endpoint_url: str = "http://127.0.0.1:8000/v1/intent", timeout_sec: float = 0.05):
        self.endpoint_url = endpoint_url
        self.timeout_sec = timeout_sec

    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResponse:
        import requests
        start_t = time.time()
        try:
            resp = requests.post(
                self.endpoint_url,
                json=request.to_dict(),
                timeout=self.timeout_sec,
            )
            latency_ms = (time.time() - start_t) * 1000.0
            if resp.status_code == 200:
                return ModelInferenceResponse.from_json(resp.text, latency_ms=latency_ms)
            else:
                return ModelInferenceResponse(
                    error=f"HTTP {resp.status_code}: {resp.text}",
                    latency_ms=latency_ms,
                )
        except Exception as e:
            latency_ms = (time.time() - start_t) * 1000.0
            return ModelInferenceResponse(error=str(e), latency_ms=latency_ms)


class JevModelPredictor(BaseIntentPredictor):
    """Wraps a BaseModelClient into the BaseIntentPredictor interface."""

    def __init__(self, client: Optional[BaseModelClient] = None):
        super().__init__()
        self.client = client or MockJevModelClient()

    def predict(
        self,
        context: SelectionContext,
        candidates: List[MacroAction],
        top_k: int = 3,
    ) -> List[IntentPrediction]:
        candidate_inputs = [
            ModelCandidateInput(
                id=c.id,
                title=c.title,
                category=c.category.value,
                description=c.description,
            )
            for c in candidates
        ]

        req = ModelInferenceRequest(
            process_name=context.process_name,
            window_title=context.window_title,
            selected_text=context.text,
            candidates=candidate_inputs,
        )

        res = self.client.infer(req)
        if res.error or not res.predictions:
            return []

        cand_map = {c.id: c for c in candidates}
        results: List[IntentPrediction] = []

        for item in res.predictions:
            if item.id in cand_map:
                macro = cand_map[item.id]
                results.append(
                    IntentPrediction(
                        macro=macro,
                        confidence=item.probability,
                        reason=f"[MODEL] {item.reason} (lat: {res.latency_ms:.1f}ms)",
                        source="model",
                    )
                )

        results.sort(key=lambda p: p.confidence, reverse=True)
        for idx, pred in enumerate(results[:top_k], start=1):
            pred.rank = idx

        return results[:top_k]
