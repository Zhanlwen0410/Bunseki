# DEPRECATED: This module is superseded by src/pipeline/semantic_pipeline.py.
# It is retained for reference only and will be removed in a future version.

from typing import Dict, List

from analyzer import DomainAnalyzer
from disambiguator import Disambiguator
from mapper import WordNetUSASMapper
from tokenizer import JapaneseTokenizer, Token


class Pipeline:
    def __init__(
        self,
        tokenizer: JapaneseTokenizer,
        mapper: WordNetUSASMapper,
        disambiguator: Disambiguator,
        analyzer: DomainAnalyzer,
    ) -> None:
        self.tokenizer = tokenizer
        self.mapper = mapper
        self.disambiguator = disambiguator
        self.analyzer = analyzer

    def _window_context(self, tokens: List[Token], index: int, window: int = 3) -> str:
        left = max(0, index - window)
        right = min(len(tokens), index + window + 1)
        return "".join(token.surface for token in tokens[left:right])

    def run(self, text: str) -> Dict[str, object]:
        tokens = self.tokenizer.tokenize(text)
        selected_domains: List[str] = []
        token_rows: List[Dict[str, object]] = []
        layer_stats = {
            "layer1_dictionary_hits": 0,
            "layer2_vector_hits": 0,
            "layer3_adjudications": 0,
        }
        for i, token in enumerate(tokens):
            # Layer 1: dictionary lookup (WordNet->USAS map).
            candidates = self.mapper.candidates(token)
            if candidates:
                layer_stats["layer1_dictionary_hits"] += 1
            # Layer 2: vector nearest-neighbor fallback for OOV terms.
            if not candidates:
                candidates = self.disambiguator.nearest_neighbor_candidates(token.lemma or token.surface)
                if candidates:
                    layer_stats["layer2_vector_hits"] += 1
            # Layer 3: final adjudication only when ambiguity remains.
            domain, _score = self.disambiguator.disambiguate(
                context=self._window_context(tokens, i),
                token=token.surface or token.lemma,
                candidates=candidates,
            )
            if len(candidates) > 1:
                layer_stats["layer3_adjudications"] += 1
            selected_domains.append(domain)
            token_rows.append(
                {
                    "surface": token.surface,
                    "lemma": token.lemma,
                    "pos": token.pos,
                    "candidates": candidates,
                    "domain": domain,
                }
            )
        return {
            "tokens": token_rows,
            "layers": layer_stats,
            "domain_count": self.analyzer.count(selected_domains),
            "domain_relative_frequency": self.analyzer.analyze(selected_domains),
        }
