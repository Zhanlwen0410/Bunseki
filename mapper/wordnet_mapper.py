import json
import re
from pathlib import Path
from typing import Dict, List

from tokenizer import Token


class WordNetUSASMapper:
    def __init__(self, mapping_path: str, unknown_domain: str = "Z99") -> None:
        self.mapping_path = Path(mapping_path)
        self.unknown_domain = unknown_domain
        self._mapping = self._load_mapping()

    def _load_mapping(self) -> Dict[str, List[str]]:
        raw = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Mapping JSON must be an object: lemma -> domain list/string.")

        result: Dict[str, List[str]] = {}
        for key, value in raw.items():
            if not isinstance(key, str):
                continue
            k = key.strip()
            if not k or k.startswith("_"):
                continue
            if isinstance(value, str):
                result[k] = [value]
            elif isinstance(value, list):
                domains = [str(item).strip() for item in value if str(item).strip()]
                result[k] = domains or [self.unknown_domain]
            else:
                result[k] = [self.unknown_domain]
        return result

    def candidates(self, token: Token) -> List[str]:
        by_lemma = self._mapping.get(token.lemma, [])
        if by_lemma:
            return by_lemma
        by_surface = self._mapping.get(token.surface, [])
        if by_surface:
            return by_surface
        return []

    def labeled_lexicon(self) -> Dict[str, List[str]]:
        return dict(self._mapping)
