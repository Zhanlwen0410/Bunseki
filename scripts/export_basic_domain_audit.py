"""Export per-token basic/final USAS audit CSV.

Usage:
  python scripts/export_basic_domain_audit.py --input sample.txt --output audit.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.main import build_result, default_lexicon_path
from src.utils.file_io import read_text_file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Input text file")
    p.add_argument("--output", required=True, help="Output CSV file")
    p.add_argument("--language", default="ja", choices=["ja", "zh", "en"])
    p.add_argument("--mode", default="C", choices=["A", "B", "C"])
    p.add_argument("--lexicon", default=default_lexicon_path())
    p.add_argument("--categories", default="data/usas_categories.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    text = read_text_file(args.input)
    result = build_result(
        text=text,
        lexicon_path=args.lexicon,
        categories_path=args.categories,
        language=args.language,
        mode=args.mode,
    )
    rows = result.get("tokens", [])
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "index",
                "surface",
                "lemma",
                "pos",
                "basic_domain_code",
                "basic_domain_source",
                "final_domain_code",
                "changed",
            ]
        )
        for idx, tok in enumerate(rows, start=1):
            basic = str(tok.get("basic_domain_code", "Z99"))
            final = str(tok.get("domain_code", "Z99"))
            w.writerow(
                [
                    idx,
                    str(tok.get("surface", "")),
                    str(tok.get("lemma", "")),
                    str(tok.get("pos", "")),
                    basic,
                    str(tok.get("basic_domain_source", "")),
                    final,
                    "1" if basic != final else "0",
                ]
            )


if __name__ == "__main__":
    main()
