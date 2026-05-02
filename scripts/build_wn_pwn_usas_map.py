"""Bootstrap synset->USAS mapping from existing lemma map.

Usage:
  python scripts/build_wn_pwn_usas_map.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import wn


ROOT = Path(__file__).resolve().parents[1]
LEMMA_MAP_PATH = ROOT / "data" / "mapping" / "wordnet_usas_map.json"
OUT_PATH = ROOT / "data" / "mapping" / "wn_pwn_usas_map.json"


def load_lemma_map() -> dict[str, list[str]]:
    raw = json.loads(LEMMA_MAP_PATH.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for lemma, labels in raw.items():
        if not isinstance(lemma, str) or lemma.startswith("_"):
            continue
        if isinstance(labels, str):
            v = [labels.strip()] if labels.strip() else []
        elif isinstance(labels, list):
            v = [str(x).strip() for x in labels if str(x).strip()]
        else:
            v = []
        if lemma.strip() and v:
            out[lemma.strip()] = v
    return out


def main() -> int:
    lemma_map = load_lemma_map()
    if not lemma_map:
        print("No lemma->USAS seeds found.")
        return 1

    try:
        w = wn.Wordnet("omw-ja:2.0")
    except Exception:
        wn.download("omw-ja:2.0")
        w = wn.Wordnet("omw-ja:2.0")

    synset_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for lemma, labels in lemma_map.items():
        synsets = w.synsets(lemma)
        for syn in synsets:
            sid = str(syn.id)
            for label in labels:
                synset_votes[sid][label] += 1

    out: dict[str, object] = {
        "_meta": {
            "description": "Auto-generated omw-ja synset -> USAS labels",
            "source": "Bootstrapped from wordnet_usas_map.json",
            "lexicon": "omw-ja:2.0",
        }
    }
    for sid, votes in sorted(synset_votes.items()):
        labels = [k for k, _ in sorted(votes.items(), key=lambda item: item[1], reverse=True)]
        if labels:
            out[sid] = labels

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with {len(out) - 1} synset mappings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
