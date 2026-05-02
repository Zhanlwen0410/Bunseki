from __future__ import annotations

from typing import Any, Dict


def compare_frequency_maps(
    left: Dict[str, int],
    right: Dict[str, int],
    top_n: int | None = None,
) -> list[Dict[str, Any]]:
    keys = sorted(set(left) | set(right))
    rows = []
    for key in keys:
        left_count = left.get(key, 0)
        right_count = right.get(key, 0)
        rows.append(
            {
                "key": key,
                "left_count": left_count,
                "right_count": right_count,
                "delta": left_count - right_count,
            }
        )

    rows.sort(key=lambda item: (abs(item["delta"]), item["left_count"] + item["right_count"]), reverse=True)
    if top_n is not None:
        rows = rows[:top_n]
    return rows


def build_comparison(left_result: Dict[str, Any], right_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "lemma_comparison": compare_frequency_maps(
            left_result.get("lemma_frequency", {}),
            right_result.get("lemma_frequency", {}),
        ),
        "domain_comparison": compare_frequency_maps(
            left_result.get("domain_frequency", {}),
            right_result.get("domain_frequency", {}),
        ),
        "summary": {
            "left_token_count": left_result.get("summary", {}).get("token_count", 0),
            "right_token_count": right_result.get("summary", {}).get("token_count", 0),
            "left_unique_lemma_count": left_result.get("summary", {}).get("unique_lemma_count", 0),
            "right_unique_lemma_count": right_result.get("summary", {}).get("unique_lemma_count", 0),
        },
    }
