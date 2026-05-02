"""Abstract interface for all LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """All LLM clients must implement this interface."""

    @abstractmethod
    def classify_source_domain(
        self,
        word: str,
        basic_meaning: str,
        candidates: list[tuple[str, str]],  # [(tag, ja_description), ...]
    ) -> str:
        """Choose best USAS source-domain tag from candidates. Returns tag string."""
        ...

    @abstractmethod
    def confirm_mrw(
        self,
        word: str,
        basic_meaning: str,
        sentence: str,
    ) -> bool:
        """Confirm if word is used metaphorically in sentence."""
        ...

    @abstractmethod
    def identify_target_domain(
        self,
        word: str,
        sentence: str,
        source_tag: str,
        all_tags: dict[str, str],  # {tag: ja_description}
    ) -> str:
        """Identify target domain USAS tag from context."""
        ...


def parse_choice(choice: str, candidates: list[tuple[str, str]], default: str = "") -> str:
    """Parse A/B/C letter response from LLM and return the selected tag."""
    c = (choice or "").strip().upper()
    idx = ord(c[0]) - 65 if c and c[0].isalpha() else -1
    if 0 <= idx < len(candidates):
        return candidates[idx][0]
    return default or (candidates[0][0] if candidates else "Z99")
