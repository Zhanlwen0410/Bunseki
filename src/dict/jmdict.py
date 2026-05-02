from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class JMdict:
    """Local JMdict lookup helper.

    Supported sources (first match wins):
    - data/jmdict/jmdict_first_gloss.json  (fast cache: lemma -> gloss string)
    - data/jmdict/JMdict_e.xml            (JMdict XML; slower, parsed once)
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._cache: dict[str, str] | None = None
        self._xml_index: dict[str, str] | None = None

    def _json_cache_path(self) -> Path:
        return self.base_dir / "data" / "jmdict" / "jmdict_first_gloss.json"

    def _xml_path(self) -> Path:
        return self.base_dir / "data" / "jmdict" / "JMdict_e.xml"

    def _load_json_cache(self) -> dict[str, str] | None:
        path = self._json_cache_path()
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        out: dict[str, str] = {}
        for k, v in raw.items():
            if not isinstance(k, str):
                continue
            key = k.strip()
            val = str(v).strip()
            if key and val:
                out[key] = val
        return out

    def _load_xml_index(self) -> dict[str, str] | None:
        xml_path = self._xml_path()
        if not xml_path.exists():
            return None
        # Lazy import to keep startup light for users without JMdict.
        import xml.etree.ElementTree as ET

        # Build a minimal lemma->first gloss index in-memory.
        # Notes:
        # - JMdict entries can have multiple keb/reb; we index all.
        # - We pick the first <gloss> under the first <sense>.
        index: dict[str, str] = {}
        context = ET.iterparse(str(xml_path), events=("end",))
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
        return index

    def lookup_first_gloss(self, lemma: str) -> Optional[str]:
        key = str(lemma or "").strip()
        if not key:
            return None

        if self._cache is None:
            self._cache = self._load_json_cache() or {}
        hit = self._cache.get(key)
        if hit:
            return hit

        if self._xml_index is None:
            self._xml_index = self._load_xml_index() or {}
        gloss = self._xml_index.get(key)
        if gloss:
            # opportunistic memoization for this process
            self._cache[key] = gloss
        return gloss

