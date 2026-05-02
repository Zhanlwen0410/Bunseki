from __future__ import annotations

from collections import Counter
from typing import Dict, List


def compute_domain_frequency(
    tagged_tokens: List[Dict[str, str]],
    min_count: int = 1,
    top_n: int | None = None,
) -> Dict[str, int]:
    counter = Counter()

    for token in tagged_tokens:
        domain_code = token.get("domain_code", "Z99").strip() or "Z99"
        counter[domain_code] += 1

    items = [(domain, count) for domain, count in counter.most_common() if count >= min_count]
    if top_n is not None:
        items = items[:top_n]
    return dict(items)
