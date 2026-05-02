from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


@dataclass(frozen=True)
class MRWResult:
    distance: float
    similarity: float
    method: str


class MRWEncoder:
    def __init__(
        self,
        model_name_or_path: str = "tohoku-nlp/bert-base-japanese-v3",
        *,
        local_files_only: bool = False,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.local_files_only = local_files_only
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, local_files_only=local_files_only)
        self.model = AutoModel.from_pretrained(model_name_or_path, local_files_only=local_files_only)
        self.model.eval()

    @torch.inference_mode()
    def _encode(self, sentence: str) -> tuple[torch.Tensor, list[int]]:
        inputs = self.tokenizer(sentence, return_tensors="pt", truncation=True, max_length=128)
        out = self.model(**inputs)
        hidden = out.last_hidden_state.squeeze(0)  # (seq, dim)
        ids = inputs["input_ids"].squeeze(0).tolist()
        return hidden, ids

    @torch.inference_mode()
    def word_vector(self, sentence: str, word: str) -> tuple[torch.Tensor, str]:
        hidden, ids = self._encode(sentence)
        tok = self.tokenizer(word, add_special_tokens=False, return_tensors="pt")
        word_ids = tok["input_ids"].squeeze(0).tolist()
        if not word_ids:
            return hidden[0], "cls_fallback_empty_word"

        def _find_subsequence(seq: list[int], sub: list[int]) -> int:
            if not sub or len(sub) > len(seq):
                return -1
            for i in range(0, len(seq) - len(sub) + 1):
                if seq[i : i + len(sub)] == sub:
                    return i
            return -1

        start = _find_subsequence(ids, word_ids)
        if start < 0:
            return hidden[0], "cls_fallback_no_span"
        end = start + len(word_ids)
        return hidden[start:end].mean(dim=0), "span_mean"

    @torch.inference_mode()
    def mrw_distance(self, basic_sentence: str, context_sentence: str, word: str) -> MRWResult:
        v_basic, m1 = self.word_vector(basic_sentence, word)
        v_ctx, m2 = self.word_vector(context_sentence, word)
        sim = F.cosine_similarity(v_basic.unsqueeze(0), v_ctx.unsqueeze(0)).item()
        dist = float(1.0 - sim)
        return MRWResult(distance=dist, similarity=float(sim), method=f"{m1}|{m2}")

