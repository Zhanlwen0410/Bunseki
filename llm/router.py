"""LLM router with fallback chain and SQLite caching.

Tries providers in order until one succeeds.
Caches results to avoid redundant API calls.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from config.settings import (
    API_KEYS,
    CACHE_DB,
    LLM_FALLBACK_CHAIN,
    LLM_PROVIDER,
    LOCAL_MODEL_PATH,
    is_llm_available,
)
from llm.base import LLMClient


def build_client(provider: str) -> LLMClient:
    """Factory: build an LLM client for the given provider."""
    key = API_KEYS.get(provider, "")
    if provider == "deepseek":
        from llm.openai_client import OpenAICompatibleClient

        return OpenAICompatibleClient(
            api_key=key,
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
        )
    elif provider == "openai":
        from llm.openai_client import OpenAICompatibleClient

        return OpenAICompatibleClient(api_key=key, model="gpt-4o-mini")
    elif provider == "gemini":
        from llm.gemini_client import GeminiClient

        return GeminiClient(api_key=key)
    elif provider == "claude":
        from llm.anthropic_client import AnthropicClient

        return AnthropicClient(api_key=key)
    elif provider == "local":
        from llm.local_client import LocalLLMClient

        return LocalLLMClient(model_path=LOCAL_MODEL_PATH)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


class LLMRouter:
    """Routes LLM requests through a fallback chain with SQLite caching."""

    def __init__(self):
        self._init_cache()
        chain = [LLM_PROVIDER] + [p for p in LLM_FALLBACK_CHAIN if p != LLM_PROVIDER]
        self.clients: list[tuple[str, LLMClient]] = []
        for provider in chain:
            try:
                client = build_client(provider)
                self.clients.append((provider, client))
            except Exception:
                pass  # skip unavailable providers

    def _init_cache(self) -> None:
        cache_path = Path(CACHE_DB)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(cache_path))
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                key TEXT PRIMARY KEY,
                result TEXT,
                provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def _cache_key(self, method: str, **kwargs: Any) -> str:
        content = json.dumps(
            {"method": method, **kwargs}, ensure_ascii=False, sort_keys=True
        )
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT result FROM llm_cache WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def _set_cache(self, key: str, result: str, provider: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO llm_cache (key, result, provider) VALUES (?,?,?)",
            (key, result, provider),
        )
        self.conn.commit()

    def _call_with_fallback(self, method_name: str, cache_key: str, **kwargs: Any) -> Any:
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        last_error: Exception | None = None
        for provider_name, client in self.clients:
            try:
                method = getattr(client, method_name)
                result = method(**kwargs)
                self._set_cache(cache_key, str(result), provider_name)
                return result
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"All LLM providers failed for {method_name}. Last error: {last_error}"
        )

    def classify_source_domain(
        self,
        word: str,
        basic_meaning: str,
        candidates: list[tuple[str, str]],
    ) -> str:
        key = self._cache_key(
            "classify_source_domain", word=word, meaning=basic_meaning
        )
        result = self._call_with_fallback(
            "classify_source_domain", key,
            word=word, basic_meaning=basic_meaning, candidates=candidates,
        )
        return str(result)

    def confirm_mrw(self, word: str, basic_meaning: str, sentence: str) -> bool:
        key = self._cache_key("confirm_mrw", word=word, sentence=sentence)
        result = self._call_with_fallback(
            "confirm_mrw", key,
            word=word, basic_meaning=basic_meaning, sentence=sentence,
        )
        return result == "True" or result is True

    def identify_target_domain(
        self,
        word: str,
        sentence: str,
        source_tag: str,
        all_tags: dict[str, str],
    ) -> str:
        key = self._cache_key(
            "identify_target_domain", word=word, sentence=sentence, src=source_tag
        )
        result = self._call_with_fallback(
            "identify_target_domain", key,
            word=word, sentence=sentence,
            source_tag=source_tag, all_tags=all_tags,
        )
        return str(result)

    def close(self) -> None:
        """Close the SQLite connection."""
        try:
            self.conn.close()
        except Exception:
            pass
