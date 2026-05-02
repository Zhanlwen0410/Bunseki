from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    surface: str
    lemma: str
    pos: str
