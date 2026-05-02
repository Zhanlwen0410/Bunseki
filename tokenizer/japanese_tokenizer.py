from typing import List

from src.preprocessing.tokenizer import create_tokenizer

from .base import Token


class JapaneseTokenizer:
    def __init__(
        self,
        tokenizer: str = "sudachi",
        mode: str = "C",
        *,
        content_pos_prefixes: tuple[str, ...] = ("名詞", "動詞", "形容詞", "副詞", "連体詞"),
    ) -> None:
        self._impl = create_tokenizer(tokenizer=tokenizer, mode=mode)
        self._content_pos_prefixes = content_pos_prefixes

    def tokenize(self, text: str) -> List[Token]:
        items = self._impl.tokenize(text)
        tokens = [Token(surface=s, lemma=l, pos=p) for s, l, p in items]
        return [tok for tok in tokens if tok.pos and tok.pos.split(",")[0] in self._content_pos_prefixes]
