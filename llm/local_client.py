"""Local LLM via llama-cpp-python (offline fallback)."""

from __future__ import annotations

from llm.base import LLMClient, parse_choice

_LLAMA_AVAILABLE = False
try:
    from llama_cpp import Llama  # type: ignore

    _LLAMA_AVAILABLE = True
except ImportError:
    pass


class LocalLLMClient(LLMClient):
    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: int = 4):
        if not _LLAMA_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is not installed. Install it manually: pip install llama-cpp-python"
            )
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=0,
            verbose=False,
        )

    def _chat(self, prompt: str) -> str:
        response = self.llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0,
            stop=["\n", "。", ".", " "],
        )
        return response["choices"][0]["message"]["content"].strip()

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
            f"「{word}」（意味：{basic_meaning}）の源領域を一文字で選択：\n"
            f"{options}\n"
            f"回答："
        )
        return parse_choice(self._chat(prompt), candidates)

    def confirm_mrw(self, word: str, basic_meaning: str, sentence: str) -> bool:
        prompt = f"「{word}」は「{sentence}」で比喩的か？はい/いいえ："
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
        ][:6]
        options = "\n".join(
            f"{chr(65 + i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = (
            f"「{word}」（「{sentence}」）の目標領域を一文字で：\n"
            f"{options}\n"
            f"回答："
        )
        return parse_choice(self._chat(prompt), candidates, default="Z99")

    @classmethod
    def is_available(cls) -> bool:
        return _LLAMA_AVAILABLE
