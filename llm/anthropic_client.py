"""Claude (Anthropic) client."""

from __future__ import annotations

from llm.base import LLMClient, parse_choice

_ANTHROPIC_AVAILABLE = False
try:
    import anthropic  # type: ignore

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is not installed. Run: pip install anthropic"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _chat(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0]
        return (content.text if hasattr(content, "text") else str(content)).strip()

    def classify_source_domain(
        self,
        word: str,
        basic_meaning: str,
        candidates: list[tuple[str, str]],
    ) -> str:
        options = "\n".join(
            f"{chr(65 + i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = (
            f"「{word}」（基本義：{basic_meaning}）の源領域USASカテゴリを一文字で：\n"
            f"{options}\n"
            f"回答："
        )
        return parse_choice(self._chat(prompt), candidates)

    def confirm_mrw(self, word: str, basic_meaning: str, sentence: str) -> bool:
        prompt = (
            f"「{sentence}」の「{word}」（基本義：{basic_meaning}）は比喩的？「はい」か「いいえ」："
        )
        return "はい" in self._chat(prompt)

    def identify_target_domain(
        self,
        word: str,
        sentence: str,
        source_tag: str,
        all_tags: dict[str, str],
    ) -> str:
        candidates = [
            (tag, desc)
            for tag, desc in all_tags.items()
            if tag != source_tag and not tag.startswith("Z")
        ][:8]
        options = "\n".join(
            f"{chr(65 + i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = (
            f"「{sentence}」で「{word}」の目標領域を一文字で：\n"
            f"{options}\n"
            f"回答："
        )
        return parse_choice(self._chat(prompt), candidates, default="Z99")

    @classmethod
    def is_available(cls) -> bool:
        return _ANTHROPIC_AVAILABLE
