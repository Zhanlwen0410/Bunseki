from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

from src.utils.category_labels import localize_category_label
from src.utils.file_io import read_json_file


TokenTuple = Tuple[str, str, str]
TaggedToken = Dict[str, object]


class SemanticTagger:
    def __init__(
        self,
        lexicon_path: str,
        categories_path: str,
        unknown_domain: str = "Z99",
        language: str = "en",
    ) -> None:
        self.lexicon_path = Path(lexicon_path)
        self.categories_path = Path(categories_path)
        self.unknown_domain = unknown_domain
        self.language = language
        self.domain_lookup = self._load_lexicon()
        self.categories = self._load_categories()

    def _load_lexicon(self) -> Dict[str, List[str]]:
        lexicon = read_json_file(str(self.lexicon_path))
        if not isinstance(lexicon, dict):
            raise ValueError("Lexicon JSON must be a dictionary of domain code -> word list.")

        lookup: Dict[str, List[str]] = {}
        for domain_code, words in lexicon.items():
            if not isinstance(domain_code, str):
                raise ValueError("Each domain code must be a string.")
            if not isinstance(words, list):
                raise ValueError(f"Words for domain '{domain_code}' must be a list.")

            for word in words:
                if not isinstance(word, str):
                    raise ValueError(f"Lexicon entry in domain '{domain_code}' must be a string.")
                for variant in self._lexicon_variants(word):
                    bucket = lookup.setdefault(variant, [])
                    if domain_code not in bucket:
                        bucket.append(domain_code)

        return lookup

    @staticmethod
    def _normalize_text(text: str) -> str:
        value = unicodedata.normalize("NFKC", text or "").strip()
        value = value.replace("ヶ", "ケ").replace("ヵ", "カ")
        return value

    def _lexicon_variants(self, word: str) -> List[str]:
        normalized = self._normalize_text(word)
        if not normalized:
            return []

        variants = {normalized}
        if normalized.startswith("御") and len(normalized) > 1:
            variants.add("ご" + normalized[1:])
            variants.add("お" + normalized[1:])
        if normalized.startswith("ご") and len(normalized) > 1:
            variants.add("御" + normalized[1:])
        if normalized.startswith("お") and len(normalized) > 1:
            variants.add("御" + normalized[1:])
        return [item for item in variants if item]

    def _load_categories(self) -> Dict[str, Dict[str, str]]:
        categories = read_json_file(str(self.categories_path))
        if not isinstance(categories, dict):
            raise ValueError("USAS categories JSON must be a dictionary.")
        return categories

    def resolve_domain_label(self, domain_code: str) -> str:
        return localize_category_label(self.categories, domain_code, self.language)

    def resolve_domain_labels(self, domain_codes: List[str]) -> List[str]:
        out: List[str] = []
        for code in domain_codes:
            label = self.resolve_domain_label(code)
            if label not in out:
                out.append(label)
        return out

    def tag_tokens(self, tokens: List[TokenTuple]) -> List[TaggedToken]:
        tagged_tokens: List[TaggedToken] = []

        for surface, lemma, pos in tokens:
            normalized_lemma = self._normalize_text(lemma)
            normalized_surface = self._normalize_text(surface)
            domain_codes = list(self.domain_lookup.get(normalized_lemma, []))
            if not domain_codes:
                domain_codes = list(self.domain_lookup.get(normalized_surface, []))
            if not domain_codes:
                domain_codes = [self.unknown_domain]
            domain_code = domain_codes[0]
            domain_labels = self.resolve_domain_labels(domain_codes)

            tagged_tokens.append(
                {
                    "surface": surface,
                    "lemma": lemma,
                    "pos": pos,
                    "domain_code": domain_code,
                    "domain_codes": domain_codes,
                    "domain_labels": domain_labels,
                    "domain_label": " / ".join(domain_labels),
                    "domain": domain_code,
                }
            )

        return tagged_tokens
