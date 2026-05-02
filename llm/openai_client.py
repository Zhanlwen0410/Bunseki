"""OpenAI-compatible client. Works for OpenAI, DeepSeek, and any OpenAI-compatible API."""

from __future__ import annotations

from llm.base import LLMClient, parse_choice

_OPENAI_AVAILABLE = False
try:
    from openai import OpenAI  # type: ignore

    _OPENAI_AVAILABLE = True
except ImportError:
    pass


class OpenAICompatibleClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        if not _OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is not installed. Run: pip install openai"
            )
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _chat(self, prompt: str, max_tokens: int = 10) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()

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
            f"この語の「源領域（source domain）」として最も適切なUSASカテゴリを選んでください。\n\n"
            f"選択肢：\n{options}\n\n"
            f"選択肢の記号（A, B, C...）を一文字だけ回答してください："
        )
        choice = self._chat(prompt, max_tokens=3)
        return parse_choice(choice, candidates)

    def confirm_mrw(self, word: str, basic_meaning: str, sentence: str) -> bool:
        prompt = (
            f"以下の文で「{word}」が比喩的（隠喩的）に使われているかを判定してください。\n\n"
            f"語の基本的な意味：{basic_meaning}\n"
            f"文：「{sentence}」\n\n"
            f"この文での「{word}」は基本的な意味とは異なる概念領域を指しますか？\n"
            f"「はい」か「いいえ」のみで回答してください："
        )
        answer = self._chat(prompt, max_tokens=5)
        return "はい" in answer or "yes" in answer.lower()

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
            f"以下の文で「{word}」は比喩的に使われています。\n"
            f"この語が「目標領域（target domain）」として指し示している概念は何ですか？\n\n"
            f"文：「{sentence}」\n"
            f"源領域（この語の字義的カテゴリ）：[{source_tag}]\n\n"
            f"目標領域として最も適切なものを選んでください：\n{options}\n\n"
            f"選択肢の記号（A, B, C...）を一文字だけ回答してください："
        )
        choice = self._chat(prompt, max_tokens=3)
        return parse_choice(choice, candidates, default="Z99")

    @classmethod
    def is_available(cls) -> bool:
        return _OPENAI_AVAILABLE
