"""Google Gemini client."""

from __future__ import annotations

from llm.base import LLMClient, parse_choice

_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai  # type: ignore

    _GEMINI_AVAILABLE = True
except ImportError:
    pass


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not _GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai package is not installed. Run: pip install google-generativeai"
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def _chat(self, prompt: str) -> str:
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=10,
                temperature=0.0,
            ),
        )
        return (response.text or "").strip()

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
            f"日本語の語「{word}」の基本的な意味は「{basic_meaning}」です。\n"
            f"源領域のUSASカテゴリを一文字（A/B/C...）で選んでください：\n"
            f"{options}\n"
            f"回答："
        )
        return parse_choice(self._chat(prompt), candidates)

    def confirm_mrw(self, word: str, basic_meaning: str, sentence: str) -> bool:
        prompt = (
            f"「{sentence}」における「{word}」（基本義：{basic_meaning}）は比喩的ですか？「はい」か「いいえ」："
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
            f"「{sentence}」で比喩的に使われた「{word}」の目標領域を一文字で選んでください：\n"
            f"{options}\n"
            f"回答："
        )
        return parse_choice(self._chat(prompt), candidates, default="Z99")

    @classmethod
    def is_available(cls) -> bool:
        return _GEMINI_AVAILABLE
