from __future__ import annotations

from typing import List, Tuple

TokenTuple = Tuple[str, str, str]


class BaseTokenizer:
    def tokenize(self, text: str) -> List[TokenTuple]:  # pragma: no cover
        raise NotImplementedError


class SudachiTokenizer(BaseTokenizer):
    def __init__(self, mode: str = "C") -> None:
        try:
            from sudachipy import dictionary, tokenizer as sudachi_tokenizer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "SudachiPy is required for tokenizer='sudachi'. Install with: python -m pip install -r requirements.txt"
            ) from exc

        self._sudachi_tokenizer = sudachi_tokenizer
        self._tokenizer = dictionary.Dictionary().create()
        self._mode = self._resolve_mode(mode)

    def _resolve_mode(self, mode: str):
        mode_map = {
            "A": self._sudachi_tokenizer.Tokenizer.SplitMode.A,
            "B": self._sudachi_tokenizer.Tokenizer.SplitMode.B,
            "C": self._sudachi_tokenizer.Tokenizer.SplitMode.C,
        }
        normalized_mode = (mode or "C").upper()
        if normalized_mode not in mode_map:
            raise ValueError("Unsupported Sudachi split mode. Choose from: A, B, C.")
        return mode_map[normalized_mode]

    def tokenize(self, text: str) -> List[TokenTuple]:
        results: List[TokenTuple] = []
        for morpheme in self._tokenizer.tokenize(text, self._mode):
            surface = morpheme.surface()
            lemma = morpheme.dictionary_form() or surface
            pos = ",".join(morpheme.part_of_speech()[:4])
            results.append((surface, lemma, pos))
        return results


class MeCabTokenizer(BaseTokenizer):
    def __init__(self, output_format: str | None = None) -> None:
        try:
            import MeCab  # type: ignore  # old mecab-python3 API
        except ImportError:
            try:
                import mecab as MeCab  # type: ignore  # new mecab API (Python 3.12+)
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "mecab-python3 is required for tokenizer='mecab'/'chasen'. Install with: python -m pip install mecab-python3"
                ) from exc

        args = ""
        if output_format:
            args = f"-O{output_format}"
        self._output_format = (output_format or "").strip().lower()
        self._tagger = MeCab.Tagger(args)

    def tokenize(self, text: str) -> List[TokenTuple]:
        out: List[TokenTuple] = []
        if self._output_format == "chasen":
            # Parse "-Ochasen" formatted output directly; avoid parseToNode() mismatch.
            raw = self._tagger.parse(text) or ""
            for line in raw.splitlines():
                if not line or line == "EOS":
                    continue
                cols = line.split("\t")
                # Typical chasen columns:
                # 0 surface, 1 reading, 2 base, 3 pos, ... (varies by dict)
                surface = cols[0].strip() if len(cols) > 0 else ""
                if not surface:
                    continue
                lemma = cols[2].strip() if len(cols) > 2 and cols[2].strip() not in ("*", "") else surface
                pos = cols[3].strip() if len(cols) > 3 else ""
                out.append((surface, lemma, pos))
            return out
        node = self._tagger.parseToNode(text)
        while node is not None:
            surface = node.surface or ""
            feat = node.feature or ""
            # BOS/EOS nodes have empty surface.
            if surface:
                parts = feat.split(",")
                # MeCab feature layout: pos1,pos2,pos3,pos4,*,*,base,reading,pron
                lemma = parts[6] if len(parts) > 6 and parts[6] not in ("*", "") else surface
                pos = ",".join((parts + ["", "", "", ""])[:4]).strip(",")
                out.append((surface, lemma, pos))
            node = node.next
        return out


def create_tokenizer(*, tokenizer: str = "sudachi", mode: str = "C") -> BaseTokenizer:
    key = (tokenizer or "sudachi").strip().lower()
    if key == "sudachi":
        return SudachiTokenizer(mode=mode)
    if key == "mecab":
        return MeCabTokenizer()
    if key == "chasen":
        # ChaSen is historically a separate analyzer; in modern setups this is commonly provided by MeCab's "-Ochasen".
        return MeCabTokenizer(output_format="chasen")
    raise ValueError("Unsupported tokenizer. Choose from: sudachi, mecab, chasen.")
