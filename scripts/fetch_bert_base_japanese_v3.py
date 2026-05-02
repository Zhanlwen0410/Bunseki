"""Download `tohoku-nlp/bert-base-japanese-v3` into the local `model/` folder.

Usage:
  python scripts/fetch_bert_base_japanese_v3.py

Output:
  model/bert-base-japanese-v3/  (HF snapshot, offline-loadable)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = REPO_ROOT / "model" / "bert-base-japanese-v3"
REPO_ID = "tohoku-nlp/bert-base-japanese-v3"


def main() -> int:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        print(f"Missing dependency: huggingface_hub ({exc})", file=sys.stderr)
        print("Install with: python -m pip install huggingface_hub", file=sys.stderr)
        return 2

    # Reduce Windows friction: avoid symlinks.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {REPO_ID} -> {TARGET_DIR}")
    snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(TARGET_DIR),
        local_dir_use_symlinks=False,
        # Keep everything needed for offline load.
        allow_patterns=[
            "config.json",
            "tokenizer_config.json",
            "vocab.txt",
            "tokenizer.json",
            "special_tokens_map.json",
            "pytorch_model.bin",
            "model.safetensors",
            "*.txt",
            "*.json",
        ],
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

