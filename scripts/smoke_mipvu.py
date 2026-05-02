"""Smoke check for the MIPVU 4-layer metaphor pipeline (Layer1-3 fields).

Usage:
  python scripts/smoke_mipvu.py

Notes:
  - Layer3 stub is enabled via env var for this smoke:
      BUNSEKI_ENABLE_MIPVU_LAYER3=1
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.main import build_result  # noqa: E402


def main() -> int:
    os.environ.setdefault("BUNSEKI_ENABLE_MIPVU_LAYER3", "1")
    text = "彼女の言葉は刃のように刺さった。"
    result = build_result(
        text=text,
        lexicon_path=str(REPO_ROOT / "data" / "lexicon.json"),
        categories_path=str(REPO_ROOT / "data" / "usas_categories.json"),
        language="ja",
        mode="C",
        min_frequency=1,
        use_bert_wsd=False,
    )
    tokens = result.get("tokens", [])
    assert isinstance(tokens, list) and tokens, "no tokens"

    # Verify schema: MRW fields should exist for all tokens (even if defaulted).
    for tok in tokens:
        assert "mrw_distance" in tok, tok
        assert "is_metaphor_candidate" in tok, tok

    # Ensure at least one token has Layer1 fields attached (content tokens).
    has_layer1 = any("basic_meaning" in t and "source_domain_label" in t for t in tokens)
    assert has_layer1, "no Layer1 fields found on any token"

    # If Layer3 enabled and we have candidates, ensure mipvu exists for some token.
    candidates = [t for t in tokens if t.get("is_metaphor_candidate")]
    if candidates:
        assert any("mipvu" in t for t in candidates), "candidate tokens missing mipvu adjudication"

    print("smoke_mipvu OK")
    print(f"layers: {result.get('layers', {})}")
    for t in candidates[:5]:
        print(
            {
                "surface": t.get("surface"),
                "lemma": t.get("lemma"),
                "mrw_distance": t.get("mrw_distance"),
                "basic_meaning": (t.get("basic_meaning") or "")[:80],
                "source_domain_label": t.get("source_domain_label"),
                "mipvu": t.get("mipvu"),
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

