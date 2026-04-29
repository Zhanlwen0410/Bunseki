"""Thin analysis controller for Tk GUI orchestration.

This module isolates non-UI analysis flow from the large Tk view class.
"""

from __future__ import annotations

from typing import Any, Optional

from src.analysis.context import build_domain_profile_rows, build_domain_word_rows
from src.services.analysis_service import analyze_with_profile


def parse_numeric_options(min_frequency_raw: str, top_n_raw: str) -> tuple[int, Optional[int]]:
    min_frequency = int((min_frequency_raw or "").strip() or "1")
    top_n_text = (top_n_raw or "").strip()
    top_n = int(top_n_text) if top_n_text else None
    if min_frequency < 1:
        raise ValueError("Min Freq must be at least 1.")
    if top_n is not None and top_n < 1:
        raise ValueError("Top N must be at least 1.")
    return min_frequency, top_n


def run_analysis(
    *,
    text: str,
    lexicon_path: str,
    categories_path: str,
    categories: dict[str, Any],
    language: str,
    mode: str,
    unknown_domain: str,
    min_frequency_raw: str,
    top_n_raw: str,
) -> dict[str, Any]:
    min_frequency, top_n = parse_numeric_options(min_frequency_raw, top_n_raw)
    data = analyze_with_profile(
        text=text,
        lexicon_path=lexicon_path,
        categories_path=categories_path,
        categories=categories,
        language=language,
        mode=mode,
        unknown_domain=unknown_domain or "Z99",
        min_frequency=min_frequency,
        top_n=top_n,
        include_profile=False,
    )
    return data["result"]


def build_profile_rows(
    *,
    tokens: list[dict[str, Any]],
    categories: dict[str, Any],
    language: str,
) -> list[dict[str, Any]]:
    return build_domain_profile_rows(
        tokens=tokens,
        categories=categories,
        language=language,
    )


def build_domain_word_table_rows(tokens: list[dict[str, Any]], domain_code: str) -> list[tuple[Any, ...]]:
    rows = build_domain_word_rows(tokens, domain_code)
    return [
        (item["word"], item["lemma"], item["frequency"], item["relative_per_10k"], item["concordance"])
        for item in rows
    ]


def build_profile_summary_lines(
    row: dict[str, Any],
    *,
    tr_fn,
    extra_t_fn,
    language: str,
) -> list[str]:
    return [
        f"{tr_fn(language, 'domain_code')}: {row['domain_code']}",
        f"{tr_fn(language, 'domain_label')}: {row['domain_label']}",
        f"{extra_t_fn('official_desc')}: {row['description']}",
        f"{extra_t_fn('types_tokens')}: {row['types']} / {row['tokens']}",
        f"{tr_fn(language, 'count')}: {row['frequency']}",
        f"{extra_t_fn('relative_10k')}: {row['relative_per_10k']}",
    ]
