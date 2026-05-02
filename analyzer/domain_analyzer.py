# DEPRECATED: This module is superseded by src/statistics/.
# It is retained for reference only and will be removed in a future version.

from collections import Counter
from typing import Dict, List


class DomainAnalyzer:
    def analyze(self, domains: List[str]) -> Dict[str, float]:
        counter = Counter(domains)
        total = sum(counter.values()) or 1
        return {key: value / total for key, value in counter.items()}

    def count(self, domains: List[str]) -> Dict[str, int]:
        return dict(Counter(domains))
