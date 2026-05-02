from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from disambiguator.wsd import Disambiguator
from model.bert_encoder import BertEncoder


@dataclass
class PipelineDecision:
    final_domain: str
    used_vector: bool
    used_mrw_fallback: bool
    vector_candidates: list[str]
    mrw_candidates: list[str]
    scores_by_domain: dict[str, dict[str, float]]


class SemanticPipeline:
    def __init__(
        self,
        *,
        model_dir: str,
        domain_descriptions: dict[str, str],
        labeled_lexicon: dict[str, list[str]],
        top_k: int = 3,
    ) -> None:
        self.encoder = BertEncoder(model_dir=model_dir)
        self.disambiguator = Disambiguator(
            self.encoder,
            domain_descriptions=domain_descriptions,
            labeled_lexicon=labeled_lexicon,
        )
        self.domain_descriptions = domain_descriptions
        self.top_k = int(max(1, top_k))
        self._domain_emb_cache: dict[str, torch.Tensor] = {}

    def _to_numpy(self, emb: torch.Tensor) -> np.ndarray:
        return emb.detach().cpu().numpy().astype(np.float32)

    def get_embedding(self, *, text: str, token: str | None = None) -> np.ndarray:
        if token:
            emb = self.encoder.encode_token_in_context(text, token)
        else:
            emb = self.encoder.encode(text)
        arr = self._to_numpy(emb)
        assert arr is not None
        assert not np.isnan(arr).any()
        assert float(np.linalg.norm(arr)) > 0.0
        return arr

    def _domain_embedding(self, domain: str) -> torch.Tensor:
        cached = self._domain_emb_cache.get(domain)
        if cached is not None:
            return cached
        prompt = self.domain_descriptions.get(domain, domain)
        emb = self.encoder.encode(prompt)
        self._domain_emb_cache[domain] = emb
        return emb

    def get_candidates_vector(self, *, token: str, context: str, domain_pool: list[str]) -> tuple[list[str], dict[str, float]]:
        if not domain_pool:
            return [], {}
        q_np = self.get_embedding(text=context, token=token)
        q = torch.from_numpy(q_np)
        scores: list[tuple[str, float]] = []
        for domain in domain_pool:
            d = self._domain_embedding(domain)
            sim = float(F.cosine_similarity(q.unsqueeze(0), d.unsqueeze(0)).item())
            if np.isnan(sim):
                continue
            scores.append((domain, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[: self.top_k]
        return [d for d, _ in top], {d: s for d, s in top}

    def get_candidates_mrw(self, *, token: str) -> list[str]:
        return self.disambiguator.nearest_neighbor_candidates(token, top_k=self.top_k, min_similarity=0.05)[: self.top_k]

    def _ontology_category(self, domain: str) -> str:
        code = str(domain or "").upper()
        if code.startswith(("S5", "P1", "G1", "H1", "M7")):
            return "institution"
        if code.startswith(("S2", "S1", "Z1", "Z8")):
            return "human"
        if code.startswith(("B1", "B2", "B3")):
            return "body"
        if code.startswith(("X", "A", "T", "N", "Q")):
            return "abstract"
        if code.startswith(("M1", "M2", "K5", "I3")):
            return "action"
        return "abstract"

    def _domain_prior(self, *, domain: str, prior_candidates: list[str]) -> float:
        if not prior_candidates:
            return 0.0
        if domain not in prior_candidates:
            return 0.0
        idx = prior_candidates.index(domain)
        return max(0.0, 1.0 - (idx * 0.25))

    def _lexical_match(self, *, token: str, domain: str) -> float:
        t = str(token or "")
        if not t:
            return 0.0
        # lightweight lexical priors; deterministic and easy to debug
        if any(k in t for k in ("学校", "大学", "会社", "病院")) and domain.startswith(("S5", "P1", "H1", "I2")):
            return 1.0
        if any(k in t.lower() for k in ("he", "she", "they", "him", "her")) and domain.startswith(("S2", "S1", "Z8")):
            return 1.0
        return 0.0

    def _mismatch_penalty(self, *, token: str, domain: str) -> float:
        t = str(token or "")
        cat = self._ontology_category(domain)
        penalty = 0.0
        # Prevent obvious drift:
        if any(k in t for k in ("学校", "大学", "会社", "病院")) and domain.startswith("S9"):
            penalty += 0.5
        if any(k in t.lower() for k in ("he", "she", "they", "him", "her")) and domain.startswith("B1"):
            penalty += 0.5
        # coarse category mismatch
        if any(k in t for k in ("学校", "大学", "会社")) and cat not in {"institution", "abstract"}:
            penalty += 0.5
        if any(k in t.lower() for k in ("he", "she", "they")) and cat not in {"human", "abstract"}:
            penalty += 0.5
        return penalty

    def adjudicate(
        self,
        *,
        token: str,
        context: str,
        prior_candidates: list[str],
        domain_pool: list[str],
    ) -> PipelineDecision:
        vector_candidates, vector_scores = self.get_candidates_vector(
            token=token,
            context=context,
            domain_pool=domain_pool,
        )
        used_vector = len(vector_candidates) > 0
        used_mrw_fallback = False
        mrw_candidates: list[str] = []
        candidates = list(vector_candidates)
        if not candidates:
            mrw_candidates = self.get_candidates_mrw(token=token)
            candidates = list(mrw_candidates)
            used_mrw_fallback = len(candidates) > 0
        if not candidates:
            return PipelineDecision(
                final_domain="Z99",
                used_vector=False,
                used_mrw_fallback=False,
                vector_candidates=[],
                mrw_candidates=[],
                scores_by_domain={},
            )

        scores_by_domain: dict[str, dict[str, float]] = {}
        best_domain = candidates[0]
        best_score = -1e9
        for d in candidates:
            emb_sim = float(vector_scores.get(d, 0.0))
            prior = float(self._domain_prior(domain=d, prior_candidates=prior_candidates))
            lexical = float(self._lexical_match(token=token, domain=d))
            final_score = 0.7 * emb_sim + 0.2 * prior + 0.1 * lexical
            penalty = float(self._mismatch_penalty(token=token, domain=d))
            final_score -= penalty
            scores_by_domain[d] = {
                "embedding_similarity": emb_sim,
                "domain_prior": prior,
                "lexical_match": lexical,
                "penalty": penalty,
                "final_score": final_score,
            }
            if final_score > best_score:
                best_score = final_score
                best_domain = d

        return PipelineDecision(
            final_domain=best_domain,
            used_vector=used_vector,
            used_mrw_fallback=used_mrw_fallback,
            vector_candidates=vector_candidates[: self.top_k],
            mrw_candidates=mrw_candidates[: self.top_k],
            scores_by_domain=scores_by_domain,
        )


def disambiguate(token: str, context: str) -> str:
    # Reserved interface for future full WSD module.
    _ = token, context
    return "Z99"

