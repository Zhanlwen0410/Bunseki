# DEPRECATED: This module is superseded by llm/router.py.
# The MIPVUStub has been replaced by real LLM clients (OpenAI, Gemini, Claude, local).
# It is retained for reference only and will be removed in a future version.

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.llm.selector import USASSelectorStub


@dataclass(frozen=True)
class StepAResult:
    step: str
    decision: str  # "A" metaphor / "B" literal
    reason: str


@dataclass(frozen=True)
class StepBResult:
    step: str
    decision: str  # "A" accept / "B" override
    source_domain_label: str
    reason: str


@dataclass(frozen=True)
class StepCResult:
    step: str
    target_domain_label: str
    free_description: str
    reason: str


class MIPVUStub:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.log_path = repo_root / "data" / "logs" / "llm_stub" / "mipvu_steps.jsonl"
        self.usas_selector = USASSelectorStub(repo_root)

    def _log(self, payload: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def step_a(self, *, sentence: str, lemma: str, basic_meaning: str, mrw_distance: float, threshold: float) -> StepAResult:
        # Stub policy: if Layer2 says it's a candidate, mark metaphor, else literal.
        decision = "A" if mrw_distance > threshold else "B"
        reason = "distance>threshold" if decision == "A" else "distance<=threshold"
        out = StepAResult(step="A", decision=decision, reason=reason)
        self._log(
            {
                "ts": time.time(),
                "step": "A",
                "lemma": lemma,
                "sentence": sentence,
                "basic_meaning": basic_meaning,
                "mrw_distance": mrw_distance,
                "threshold": threshold,
                "output": out.__dict__,
            }
        )
        return out

    def step_b(self, *, lemma: str, source_domain_label: str, candidates: Iterable[str]) -> StepBResult:
        # Stub policy: keep the existing label if it's in candidate set; otherwise pick Z99 (or first candidate).
        cands = [str(x).strip() for x in candidates if str(x).strip()]
        cands = list(dict.fromkeys(cands))
        chosen = source_domain_label if source_domain_label in cands else ("Z99" if "Z99" in cands else (cands[0] if cands else "Z99"))
        decision = "A" if chosen == source_domain_label else "B"
        reason = "accept_existing" if decision == "A" else "override_to_candidate"
        out = StepBResult(step="B", decision=decision, source_domain_label=chosen, reason=reason)
        self._log({"ts": time.time(), "step": "B", "lemma": lemma, "candidates": cands, "input": source_domain_label, "output": out.__dict__})
        return out

    def step_c(
        self,
        *,
        sentence: str,
        lemma: str,
        usas_tagset: Iterable[str],
        source_domain_label: str = "Z99",
    ) -> StepCResult:
        # Stub policy: produce a conservative free description and map back to USAS via selector stub.
        free = f"（stub）文脈における「{lemma}」の抽象的な意味"
        choice = self.usas_selector.classify_to_usas(free, usas_tagset)
        chosen = choice.label
        reason = "stub_free_then_classify"
        # Guardrail: Step C should not collapse to Z99 when Step B already has a concrete label.
        if chosen == "Z99" and source_domain_label and source_domain_label != "Z99":
            chosen = source_domain_label
            reason = "fallback_to_step_b_source_domain"
        out = StepCResult(step="C", target_domain_label=chosen, free_description=free, reason=reason)
        self._log(
            {
                "ts": time.time(),
                "step": "C",
                "lemma": lemma,
                "sentence": sentence,
                "free_description": free,
                "source_domain_label": source_domain_label,
                "selector_choice": choice.__dict__,
                "output": out.__dict__,
            }
        )
        return out

