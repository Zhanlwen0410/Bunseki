from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer, BertTokenizer
from transformers.models.bert_japanese import BertJapaneseTokenizer


class BertEncoder:
    def __init__(self, model_dir: str) -> None:
        self.model_dir = Path(model_dir)
        self._tokenizer = self._load_tokenizer()
        self._model = AutoModel.from_pretrained(
            str(self.model_dir), local_files_only=True
        )
        self._model.eval()

    def _load_tokenizer(self):
        try:
            return AutoTokenizer.from_pretrained(
                str(self.model_dir), local_files_only=True, use_fast=False
            )
        except Exception:
            try:
                # Fallback for local Japanese BERT checkpoints with vocab/config but no fast tokenizer artifacts.
                return BertJapaneseTokenizer.from_pretrained(
                    str(self.model_dir), local_files_only=True
                )
            except Exception:
                vocab_file = self.model_dir / "vocab.txt"
                if not vocab_file.exists():
                    raise
                # Last-resort fallback: plain WordPiece tokenizer from local vocab.
                return BertTokenizer(vocab_file=str(vocab_file), do_lower_case=False)

    @torch.inference_mode()
    def encode(self, text: str) -> torch.Tensor:
        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        out = self._model(**encoded)
        hidden = out.last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return pooled.squeeze(0)

    @torch.inference_mode()
    def encode_token_in_context(self, context: str, token: str) -> torch.Tensor:
        encoded_ctx = self._tokenizer(
            context,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        out_ctx = self._model(**encoded_ctx)
        ctx_hidden = out_ctx.last_hidden_state.squeeze(0)
        ctx_ids = encoded_ctx["input_ids"].squeeze(0).tolist()

        encoded_tok = self._tokenizer(
            token,
            return_tensors="pt",
            truncation=True,
            max_length=32,
            add_special_tokens=False,
        )
        tok_ids = encoded_tok["input_ids"].squeeze(0).tolist()
        if not tok_ids:
            return self.encode(context)

        def _find_subsequence(seq: list[int], sub: list[int]) -> int:
            if not sub or len(sub) > len(seq):
                return -1
            for i in range(0, len(seq) - len(sub) + 1):
                if seq[i : i + len(sub)] == sub:
                    return i
            return -1

        start = _find_subsequence(ctx_ids, tok_ids)
        if start < 0:
            return self.encode(context)
        end = start + len(tok_ids)
        return ctx_hidden[start:end].mean(dim=0)
