from collections import Counter
from typing import Dict, List


def compute_lemma_frequency(
    tagged_tokens: List[Dict[str, str]],
    min_count: int = 1,
    top_n: int | None = None,
) -> Dict[str, int]:
    counter = Counter()

    for token in tagged_tokens:
        lemma = token.get("lemma", "").strip()
        if lemma:
            counter[lemma] += 1

    items = [(lemma, count) for lemma, count in counter.most_common() if count >= min_count]
    if top_n is not None:
        items = items[:top_n]
    return dict(items)
