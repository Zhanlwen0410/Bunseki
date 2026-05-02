from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class USASChoice:
    label: str
    confidence: float
    rationale: str = ""


class USASSelectorStub:
    """Deterministic placeholder for an LLM-based USAS multiple-choice classifier.

    - Always returns a label from the provided tagset.
    - Writes a JSONL audit log so you can replay the exact inputs later.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.log_path = repo_root / "data" / "logs" / "llm_stub" / "usas_selector.jsonl"

    def _write_log(self, payload: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def classify_to_usas(self, text: str, usas_tagset: Iterable[str]) -> USASChoice:
        tags = [str(x).strip() for x in usas_tagset if str(x).strip()]
        tags = list(dict.fromkeys(tags))
        if not tags:
            return USASChoice(label="Z99", confidence=0.0, rationale="empty_tagset")

        t = str(text or "").strip()
        t_lower = t.lower()
        # Deterministic bilingual keyword rules for JMdict glosses (EN/JA mixed).
        picked = "Z99" if "Z99" in tags else tags[0]
        rationale = "stub_default"
        if any(k in t for k in ("食", "飲", "飯", "パン", "料理")) and "F1" in tags:
            picked, rationale = "F1", "keyword_food"
        elif any(k in t for k in ("学校", "大学", "教育", "学ぶ")) and "P1" in tags:
            picked, rationale = "P1", "keyword_education"
        elif any(k in t for k in ("橋", "川", "谷", "渡る", "架け")) and "M6" in tags:
            picked, rationale = "M6", "keyword_location_direction"
        elif (
            any(k in t_lower for k in ("runner-up", "champion", "tournament", "sports", "athlete", "match"))
            or re.search(r"\b(game|games|sport|sports)\b", t_lower)
        ) and ("K5.1" in tags or "K5" in tags):
            picked = "K5.1" if "K5.1" in tags else "K5"
            rationale = "keyword_sports_en"
        elif any(k in t_lower for k in ("school", "university", "education", "student", "teacher")) and "P1" in tags:
            picked, rationale = "P1", "keyword_education_en"
        elif any(k in t_lower for k in ("company", "business", "trade", "sell", "commerce")) and ("I2.1" in tags or "I2" in tags):
            picked = "I2.1" if "I2.1" in tags else "I2"
            rationale = "keyword_business_en"
        elif any(k in t_lower for k in ("hospital", "medicine", "medical", "disease", "illness")) and ("B3" in tags or "B2" in tags):
            picked = "B3" if "B3" in tags else "B2"
            rationale = "keyword_medical_en"

        out = USASChoice(label=picked, confidence=0.1 if rationale == "stub_default" else 0.35, rationale=rationale)
        self._write_log(
            {
                "ts": time.time(),
                "kind": "layer1_source_domain",
                "text": t,
                "tagset_size": len(tags),
                "choice": {"label": out.label, "confidence": out.confidence, "rationale": out.rationale},
            }
        )
        return out

