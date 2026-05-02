"""Centralized analysis + lexicon helpers for Tk GUI and WebView API."""

from __future__ import annotations

import threading
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.analysis.context import build_domain_profile_rows, build_kwic_rows
from src.main import build_result, clear_tagger_cache
from src.utils.category_labels import localize_category_label
from src.utils.file_io import read_json_file, write_json

from src.i18n import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES_SET = frozenset(SUPPORTED_LANGUAGES)
SPLIT_MODES = frozenset({"A", "B", "C"})
MAX_LEMMA_LEN = 512

_lexicon_lock = threading.Lock()


def normalize_lexicon_term(term: str) -> str:
    """Normalize a lexicon term for storage: NFKC normalization + strip."""
    value = unicodedata.normalize("NFKC", term or "").strip()
    if value.startswith("??") and len(value) > 1:
        return "??" + value[1:]
    return value


def parse_analyze_params(
    *,
    text_raw: str = "",
    language_raw: Any = "zh",
    tokenizer_raw: Any = "sudachi",
    mode_raw: Any = "C",
    min_frequency_raw: Any = 1,
    top_n_raw: Any = None,
    lexicon_path_raw: Any = None,
    default_lexicon_path: str = "",
    use_bert_wsd_raw: Any = True,
    bert_model_dir_raw: Any = None,
) -> dict[str, Any]:
    """Parse and normalize all analysis request parameters in one place.

    Returns a dict with either ``{"ok": False, "error": {...}}`` on
    validation failure or ``{"ok": True, ...}`` with all parsed values.
    """
    text = str(text_raw or "").strip()
    if not text:
        return {
            "ok": False,
            "error": {
                "code": "missing_text",
                "message": "Text is required.",
                "hint": "Paste or type Japanese text in the input area.",
            },
        }
    language = str(language_raw or "zh").strip()
    tokenizer = str(tokenizer_raw or "sudachi").strip()
    mode = str(mode_raw or "C").strip()
    try:
        min_frequency = parse_min_frequency(min_frequency_raw)
        top_n = parse_top_n(top_n_raw)
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "error": {
                "code": "invalid_number",
                "message": f"Invalid numeric option: {exc}",
                "hint": "min_frequency and top_n must be integers.",
            },
        }

    err = validate_analyze_options(
        language=language,
        tokenizer=tokenizer,
        mode=mode,
        min_frequency=min_frequency,
        top_n=top_n,
    )
    if err:
        return {"ok": False, "error": err}

    lexicon = str(lexicon_path_raw or default_lexicon_path).strip()
    if not lexicon:
        return {
            "ok": False,
            "error": {
                "code": "missing_lexicon",
                "message": "Lexicon path is empty.",
                "hint": "Set a valid lexicon JSON path.",
            },
        }

    return {
        "ok": True,
        "text": text,
        "language": language,
        "tokenizer": tokenizer,
        "mode": mode,
        "min_frequency": min_frequency,
        "top_n": top_n,
        "lexicon": lexicon,
        "use_bert_wsd": bool(use_bert_wsd_raw),
        "bert_model_dir": bert_model_dir_raw if bert_model_dir_raw else None,
    }


def safe_error_msg(exc: BaseException) -> str:
    """Return a user-safe message for display without leaking internal paths."""
    msg = str(exc).strip()
    if not msg:
        return type(exc).__name__
    import os as _os
    import pathlib as _pl

    root = str(_pl.Path(__file__).resolve().parents[2])
    return msg.replace(root, "<repo>").replace(_os.sep, "/")


def parse_min_frequency(raw: Any) -> int:
    if raw is None or raw == "":
        return 1
    return int(raw)


def parse_top_n(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return int(s)


def validate_analyze_options(
    *,
    language: str,
    tokenizer: str = "sudachi",
    mode: str = "C",
    min_frequency: int = 1,
    top_n: Optional[int] = None,
) -> Optional[Dict[str, str]]:
    """Return error dict {code, message, hint} or None if OK."""
    lang = (language or "en").strip()
    if lang not in SUPPORTED_LANGUAGES_SET:
        return {
            "code": "invalid_language",
            "message": f"Unsupported language: {language!r}.",
            "hint": f"Use one of: {', '.join(sorted(SUPPORTED_LANGUAGES))}.",
        }
    m = (mode or "C").strip().upper()
    tok = (tokenizer or "sudachi").strip().lower()
    if tok not in {"sudachi", "mecab", "chasen"}:
        return {
            "code": "invalid_tokenizer",
            "message": f"Unsupported tokenizer: {tokenizer!r}.",
            "hint": "Use sudachi, mecab, or chasen.",
        }
    if tok == "sudachi" and m not in SPLIT_MODES:
        return {
            "code": "invalid_mode",
            "message": f"Unsupported Sudachi mode: {mode!r}.",
            "hint": "Use A, B, or C.",
        }
    if min_frequency < 1:
        return {
            "code": "invalid_min_frequency",
            "message": "min_frequency must be >= 1.",
            "hint": "Set minimum frequency to 1 or higher.",
        }
    if top_n is not None and top_n < 1:
        return {
            "code": "invalid_top_n",
            "message": "top_n must be >= 1 when set.",
            "hint": "Leave top_n empty or use a positive integer.",
        }
    return None


def analyze_with_profile(
    *,
    text: str,
    lexicon_path: str,
    categories_path: str,
    categories: Dict[str, Any],
    language: str = "en",
    tokenizer: str = "sudachi",
    mode: str = "C",
    unknown_domain: str = "Z99",
    min_frequency: int = 1,
    top_n: Optional[int] = None,
    include_profile: bool = True,
    use_bert_wsd: bool = True,
    bert_model_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run full analysis; optionally attach domain profile rows (WebView needs both)."""
    result = build_result(
        text=text,
        lexicon_path=lexicon_path,
        categories_path=categories_path,
        language=language,
        tokenizer=tokenizer,
        mode=mode,
        unknown_domain=unknown_domain,
        min_frequency=min_frequency,
        top_n=top_n,
        use_bert_wsd=use_bert_wsd,
        bert_model_dir=bert_model_dir,
    )
    if not include_profile:
        return {"result": result}
    profile = build_domain_profile_rows(
        result["tokens"],
        categories,
        language=language,
    )
    return {"result": result, "profile": profile}


def kwic_from_result(
    result: Dict[str, Any],
    keyword: str,
    domain_code: str = "",
    pos_filter: str = "",
    use_regex: bool = False,
    span: int = 36,
) -> List[Dict[str, Any]]:
    if not result:
        return []
    return build_kwic_rows(
        text=str(result.get("source_text", "")),
        tokens=result.get("tokens", []),
        keyword=keyword,
        domain_code=domain_code,
        pos_filter=pos_filter,
        use_regex=use_regex,
        span=span,
    )


def lexicon_overview_payload(
    lexicon_path: Path | str,
    categories: Dict[str, Dict[str, str]],
    language: str = "en",
) -> Dict[str, Any]:
    path = Path(lexicon_path)
    lexicon = read_json_file(str(path))
    rows: List[Dict[str, Any]] = []
    for code in sorted(lexicon):
        words = lexicon[code]
        rows.append(
            {
                "domain_code": code,
                "domain_label": localize_category_label(categories, code, language),
                "count": len(words),
                "words": words[:100],
            }
        )
    return {"domains": rows, "path": str(path)}


def acquire_lexicon_lock() -> threading.Lock:
    return _lexicon_lock


def append_lexicon_terms(
    lexicon_path: Path | str,
    items: List[Dict[str, str]],
    *,
    known_domain_codes: Optional[set[str]] = None,
    default_domain: str = "Z99",
) -> Dict[str, Any]:
    """Merge lemmas into lexicon JSON; validates lightly and writes atomically."""
    path = Path(lexicon_path)
    with _lexicon_lock:
        return _append_lexicon_terms_locked(
            path, items,
            known_domain_codes=known_domain_codes,
            default_domain=default_domain,
        )


def _append_lexicon_terms_locked(
    path: Path,
    items: List[Dict[str, str]],
    *,
    known_domain_codes: Optional[set[str]] = None,
    default_domain: str = "Z99",
) -> Dict[str, Any]:
    lexicon = read_json_file(str(path))
    if not isinstance(lexicon, dict):
        raise ValueError("Lexicon file must contain a JSON object.")

    added = 0
    skipped_long = 0
    unknown_domains: set[str] = set()

    for item in items:
        domain_code = str(item.get("domain_code", "")).strip() or default_domain
        lemma = normalize_lexicon_term(str(item.get("lemma", "")))
        if not lemma:
            continue
        if len(lemma) > MAX_LEMMA_LEN:
            skipped_long += 1
            continue
        if known_domain_codes is not None and domain_code not in known_domain_codes:
            unknown_domains.add(domain_code)
        lexicon.setdefault(domain_code, [])
        if lemma not in lexicon[domain_code]:
            lexicon[domain_code].append(lemma)
            added += 1

    write_json(lexicon, path)
    clear_tagger_cache()
    out: Dict[str, Any] = {"added": added, "path": str(path)}
    if skipped_long:
        out["skipped_long"] = skipped_long
    if unknown_domains:
        out["unknown_domain_codes"] = sorted(unknown_domains)
    return out
