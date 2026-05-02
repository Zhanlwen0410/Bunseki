from collections import defaultdict
from typing import Dict, List, Tuple

import torch
import torch.nn.functional as F

from model import BertEncoder


class Disambiguator:
    def __init__(
        self,
        encoder: BertEncoder,
        domain_descriptions: Dict[str, str],
        *,
        labeled_lexicon: Dict[str, List[str]] | None = None,
    ) -> None:
        self.encoder = encoder
        self._domain_cache: Dict[str, torch.Tensor] = {}
        self._lemma_embedding_cache: Dict[str, torch.Tensor] = {}
        self._domain_descriptions = {
            str(code).strip(): str(desc).strip()
            for code, desc in domain_descriptions.items()
            if str(code).strip() and str(desc).strip()
        }
        self._labeled_lexicon = {
            str(lemma).strip(): [str(code).strip() for code in domains if str(code).strip()]
            for lemma, domains in (labeled_lexicon or {}).items()
            if str(lemma).strip() and domains
        }
        self._prime_domain_embeddings()

    def _prime_domain_embeddings(self) -> None:
        # Pre-encode all domain descriptions once and cache in memory.
        for domain, desc in self._domain_descriptions.items():
            if domain in self._domain_cache:
                continue
            self._domain_cache[domain] = self.encoder.encode(desc)

    def _domain_embedding(self, domain: str) -> torch.Tensor:
        cached = self._domain_cache.get(domain)
        if cached is not None:
            return cached
        prompt = self._domain_descriptions.get(
            domain,
            f"The semantic domain in this context is {domain}.",
        )
        emb = self.encoder.encode(prompt)
        self._domain_cache[domain] = emb
        return emb

    def _lemma_embedding(self, lemma: str) -> torch.Tensor:
        cached = self._lemma_embedding_cache.get(lemma)
        if cached is not None:
            return cached
        emb = self.encoder.encode(lemma)
        self._lemma_embedding_cache[lemma] = emb
        return emb

    def nearest_neighbor_candidates(
        self,
        token: str,
        *,
        top_k: int = 8,
        min_similarity: float = 0.15,
    ) -> List[str]:
        if not self._labeled_lexicon:
            return []
        query = self.encoder.encode(token)
        scored: List[Tuple[float, str]] = []
        for lemma in self._labeled_lexicon:
            emb = self._lemma_embedding(lemma)
            score = F.cosine_similarity(query.unsqueeze(0), emb.unsqueeze(0)).item()
            if score >= min_similarity:
                scored.append((score, lemma))
        if not scored:
            return []
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:top_k]
        votes: Dict[str, float] = defaultdict(float)
        for score, lemma in top:
            for domain in self._labeled_lexicon.get(lemma, []):
                votes[domain] += max(score, 0.0)
        ranked = sorted(votes.items(), key=lambda item: item[1], reverse=True)
        return [code for code, _ in ranked]

    def disambiguate(
        self,
        context: str,
        token: str,
        candidates: List[str],
        *,
        similarity_threshold: float = 0.2,
    ) -> Tuple[str, float]:
        if not candidates:
            return "Z99", 0.0
        if len(candidates) == 1:
            return candidates[0], 1.0
        ctx = self.encoder.encode_token_in_context(context, token)
        best = candidates[0]
        best_score = float("-inf")
        for domain in candidates:
            dom = self._domain_embedding(domain)
            score = F.cosine_similarity(ctx.unsqueeze(0), dom.unsqueeze(0)).item()
            if score > best_score:
                best_score = score
                best = domain
        if best_score < similarity_threshold:
            return "Z99", best_score
        return best, best_score
