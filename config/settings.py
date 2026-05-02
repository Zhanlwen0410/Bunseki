"""Centralized configuration for Bunseki MIPVU pipeline.

All settings are read from environment variables first, then fall back to
data/llm_config.json (which the desktop Settings UI writes to).

No API keys are hardcoded — set BUNSEKI_*_API_KEY env vars or use the Settings UI.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_LLM_CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "llm_config.json"
_LOCK = threading.RLock()

# ---------------------------------------------------------------------------
# Mutable config state (reloaded via _load())
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = "none"
LLM_FALLBACK_CHAIN: List[str] = ["deepseek", "openai", "gemini", "claude"]
API_KEYS: Dict[str, str] = {}
LOCAL_MODEL_PATH: str = "./models/qwen3-4b-q4_k_m.gguf"

# ---------------------------------------------------------------------------
# Static thresholds (from blueprint)
# ---------------------------------------------------------------------------
MRW_THRESHOLDS: Dict[str, float] = {
    "名詞-サ変可能": 0.45,
    "名詞": 0.35,
    "動詞": 0.25,
    "形容詞": 0.28,
    "副詞": 0.30,
    "default": 0.35,
}
TARGET_POS = ["名詞", "動詞", "形容詞", "副詞"]
BERT_MODEL = os.environ.get("BUNSEKI_BERT_MODEL", "model/bert-base-japanese-v3").strip()
CACHE_DB = os.environ.get("BUNSEKI_CACHE_DB", "data/llm_cache.db").strip()
LLM_MAX_TOKENS = 10
LLM_TEMPERATURE = 0.0

PROVIDER_LABELS: Dict[str, str] = {
    "none": "None (deterministic only)",
    "deepseek": "DeepSeek",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "claude": "Claude (Anthropic)",
    "local": "Local (llama-cpp)",
}
PROVIDER_KEYS: List[str] = ["none", "deepseek", "openai", "gemini", "claude", "local"]


# ---------------------------------------------------------------------------
# Load / reload
# ---------------------------------------------------------------------------

def _load() -> None:
    """Load config from env vars (priority) + JSON file (fallback)."""
    global LLM_PROVIDER, LLM_FALLBACK_CHAIN, API_KEYS, LOCAL_MODEL_PATH

    # 1. Load from JSON file first
    file_provider = ""
    file_chain: List[str] = []
    file_keys: Dict[str, str] = {}
    file_local_path = ""
    if _LLM_CONFIG_PATH.exists():
        try:
            with open(_LLM_CONFIG_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                file_provider = str(raw.get("provider", "") or "").strip()
                chain_raw = raw.get("fallback_chain")
                if isinstance(chain_raw, list):
                    file_chain = [str(x).strip() for x in chain_raw if str(x).strip()]
                keys_raw = raw.get("api_keys")
                if isinstance(keys_raw, dict):
                    file_keys = {str(k).strip(): str(v).strip() for k, v in keys_raw.items() if str(v).strip()}
                file_local_path = str(raw.get("local_model_path", "") or "").strip()
        except Exception:
            pass

    # 2. Env vars take priority
    env_provider = os.environ.get("BUNSEKI_LLM_PROVIDER", "").strip()
    env_chain_str = os.environ.get("BUNSEKI_LLM_FALLBACK_CHAIN", "").strip()
    env_deepseek = os.environ.get("BUNSEKI_DEEPSEEK_API_KEY", "").strip()
    env_openai = os.environ.get("BUNSEKI_OPENAI_API_KEY", "").strip()
    env_gemini = os.environ.get("BUNSEKI_GEMINI_API_KEY", "").strip()
    env_anthropic = os.environ.get("BUNSEKI_ANTHROPIC_API_KEY", "").strip()
    env_local = os.environ.get("BUNSEKI_LOCAL_MODEL_PATH", "").strip()

    LLM_PROVIDER = env_provider or file_provider or "none"
    LLM_FALLBACK_CHAIN = (
        [p.strip() for p in env_chain_str.split(",") if p.strip()]
        if env_chain_str
        else (file_chain or ["deepseek", "openai", "gemini", "claude"])
    )
    API_KEYS = {
        "deepseek": env_deepseek or file_keys.get("deepseek", ""),
        "openai": env_openai or file_keys.get("openai", ""),
        "gemini": env_gemini or file_keys.get("gemini", ""),
        "anthropic": env_anthropic or file_keys.get("anthropic", ""),
    }
    LOCAL_MODEL_PATH = env_local or file_local_path or "./models/qwen3-4b-q4_k_m.gguf"


# Load on import
_load()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reload_config() -> None:
    """Re-read config from env vars + JSON file (call after editing llm_config.json)."""
    with _LOCK:
        _load()


def get_llm_config_safe() -> Dict[str, Any]:
    """Return current LLM config as a dict (API keys masked for UI display)."""
    with _LOCK:
        keys_masked = {}
        for provider in PROVIDER_KEYS:
            if provider in ("none", "local"):
                continue
            raw_key = API_KEYS.get(provider, "")
            if raw_key:
                # Show first 4 + last 4 chars
                if len(raw_key) > 10:
                    keys_masked[provider] = raw_key[:4] + "****" + raw_key[-4:]
                else:
                    keys_masked[provider] = "****"
            else:
                keys_masked[provider] = ""
        return {
            "provider": LLM_PROVIDER,
            "fallback_chain": list(LLM_FALLBACK_CHAIN),
            "api_keys": keys_masked,
            "local_model_path": LOCAL_MODEL_PATH,
            "is_available": is_llm_available(),
        }


def save_llm_config(
    *,
    provider: str = "",
    fallback_chain: List[str] | None = None,
    api_keys: Dict[str, str] | None = None,
    local_model_path: str = "",
) -> Dict[str, Any]:
    """Save LLM config to data/llm_config.json and reload.

    api_keys values of "****" (unchanged mask) are ignored — the existing
    value in the file is preserved.  Only non-masked values are saved.
    """
    with _LOCK:
        # Read existing to merge unmasked keys
        existing: Dict[str, Any] = {}
        if _LLM_CONFIG_PATH.exists():
            try:
                with open(_LLM_CONFIG_PATH, encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                existing = {}
        existing_keys = existing.get("api_keys", {}) if isinstance(existing.get("api_keys"), dict) else {}

        # Merge: non-masked values from input override existing
        merged_keys: Dict[str, str] = dict(existing_keys)
        if api_keys:
            for k, v in api_keys.items():
                v = str(v or "").strip()
                if v and v != "****":  # actual new key value
                    merged_keys[k] = v
                elif not v:
                    merged_keys.pop(k, None)

        payload: Dict[str, Any] = {}
        if provider:
            payload["provider"] = provider
        if fallback_chain is not None:
            payload["fallback_chain"] = [str(x).strip() for x in fallback_chain if str(x).strip()]
        payload["api_keys"] = merged_keys
        if local_model_path:
            payload["local_model_path"] = local_model_path

        # Preserve unmentioned keys from existing
        for k, v in existing.items():
            if k not in payload:
                payload[k] = v

        _LLM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        _load()
        return get_llm_config_safe()


def is_llm_available() -> bool:
    """Return True if at least one LLM provider is configured."""
    if LLM_PROVIDER == "local":
        return Path(LOCAL_MODEL_PATH).exists()
    if LLM_PROVIDER in API_KEYS and API_KEYS[LLM_PROVIDER]:
        return True
    for provider, key in API_KEYS.items():
        if key:
            return True
    return False


def load_usas_labels_ja(path: str) -> dict[str, str]:
    """Extract {tag: ja_description} from usas_categories.json."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for code, info in raw.items():
        if isinstance(info, dict):
            desc = str(info.get("ja", "") or info.get("en", "") or code).strip()
        else:
            desc = str(info or code).strip()
        if desc:
            out[str(code).strip()] = desc
    return out
