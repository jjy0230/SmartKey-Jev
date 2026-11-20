"""
Data Contracts and Protocols for Jev Intent Model Inference.
Defines serialization format, prompt formatting, and structured output parsing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json


@dataclass
class ModelCandidateInput:
    id: str
    title: str
    category: str
    description: str


@dataclass
class ModelInferenceRequest:
    """Request payload sent to Jev Model (AnyJev / Local LLM / HTTP Endpoint)."""
    process_name: str
    window_title: str
    selected_text: str
    candidates: List[ModelCandidateInput]
    max_tokens: int = 128
    temperature: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_name": self.process_name,
            "window_title": self.window_title,
            "selected_text": self.selected_text,
            "candidates": [
                {
                    "id": c.id,
                    "title": c.title,
                    "category": c.category,
                    "description": c.description,
                }
                for c in self.candidates
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

    def format_prompt(self) -> str:
        """Constructs an aligned instruction prompt for small fine-tuned SLMs (e.g. SmolLM2 / Qwen2.5)."""
        candidate_lines = "\n".join(
            [f"- {c.id}: {c.title} ({c.description})" for c in self.candidates]
        )
        return (
            "<|im_start|>system\n"
            "You are SmartKey-Jev, a desktop intent classification head. Given the active application "
            "and the user's selected text snippet, predict the top 3 most relevant macro actions and "
            "output calibrated posterior probabilities.\n"
            "Respond ONLY with a JSON object in the format:\n"
            '{"predictions": [{"id": "<macro_id>", "probability": 0.85, "reason": "why"}]}\n'
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"[Desktop Context]\n"
            f"Process: {self.process_name}\n"
            f"Window: {self.window_title}\n"
            f"Selected Snippet (Max 300 chars):\n\"\"\"\n{self.selected_text}\n\"\"\"\n\n"
            f"[Candidate Pool ({len(self.candidates)} actions)]:\n{candidate_lines}\n\n"
            "Predict the top 3 optimal actions:\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )


@dataclass
class ModelMacroScore:
    id: str
    probability: float
    reason: str = ""


@dataclass
class ModelInferenceResponse:
    """Structured response parsed from Jev Model output."""
    predictions: List[ModelMacroScore] = field(default_factory=list)
    raw_response: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None

    @classmethod
    def from_json(cls, json_str: str, latency_ms: float = 0.0) -> ModelInferenceResponse:
        """Parse structured model output, resilient to codeblock markdown fences."""
        try:
            cleaned = json_str.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            items = data.get("predictions", [])
            scores = [
                ModelMacroScore(
                    id=item["id"],
                    probability=float(item.get("probability", 0.0)),
                    reason=item.get("reason", ""),
                )
                for item in items
                if "id" in item
            ]
            return cls(predictions=scores, raw_response=json_str, latency_ms=latency_ms)
        except Exception as e:
            return cls(predictions=[], raw_response=json_str, latency_ms=latency_ms, error=str(e))
