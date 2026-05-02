"""Build a fast lemma->first_gloss cache from JMdict_e.xml.

Output:
  data/jmdict/jmdict_first_gloss.json

Usage:
  python scripts/build_jmdict_first_gloss.py
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
XML_PATH = REPO_ROOT / "data" / "jmdict" / "JMdict_e.xml"
OUT_PATH = REPO_ROOT / "data" / "jmdict" / "jmdict_first_gloss.json"


def main() -> int:
    if not XML_PATH.exists():
        print(f"JMdict XML not found: {XML_PATH}", file=sys.stderr)
        print("Run: python scripts/fetch_jmdict.py", file=sys.stderr)
        return 2

    index: dict[str, str] = {}
    context = ET.iterparse(str(XML_PATH), events=("end",))
    for _event, elem in context:
        if elem.tag != "entry":
            continue
        kebs = [e.text.strip() for e in elem.findall("./k_ele/keb") if e.text and e.text.strip()]
        rebs = [e.text.strip() for e in elem.findall("./r_ele/reb") if e.text and e.text.strip()]
        gloss = None
        sense = elem.find("./sense")
        if sense is not None:
            g = sense.find("./gloss")
            if g is not None and g.text and g.text.strip():
                gloss = g.text.strip()
        if gloss:
            for lemma in kebs + rebs:
                index.setdefault(lemma, gloss)
        elem.clear()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT_PATH} (entries={len(index)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

