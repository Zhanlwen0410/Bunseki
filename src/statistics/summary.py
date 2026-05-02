from __future__ import annotations

from collections import Counter
from typing import Dict, List


def compute_summary(tagged_tokens: List[Dict[str, str]]) -> Dict[str, int | str]:
    domains = [
        token.get("domain_code", "Z99").strip() or "Z99"
        for token in tagged_tokens
    ]
    lemmas = [
        token.get("lemma", "").strip()
        for token in tagged_tokens
        if token.get("lemma", "").strip()
    ]
    pos_tags = [
        token.get("pos", "").strip()
        for token in tagged_tokens
        if token.get("pos", "").strip()
    ]

    domain_counter = Counter(domains)
    pos_counter = Counter(pos_tags)

    return {
        "token_count": len(tagged_tokens),
        "unique_lemma_count": len(set(lemmas)),
        "unique_domain_count": len(set(domains)),
        "most_common_domain": domain_counter.most_common(1)[0][0] if domain_counter else "",
        "most_common_pos": pos_counter.most_common(1)[0][0] if pos_counter else "",
    }
