import re
from bisect import bisect_right
from collections import Counter
from typing import Any, Dict, List

from src.utils.category_labels import localize_category_label

SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[\u3002\uff01\uff1f!?\u2026\u2025\uff5e\uff0e\u266a])\s*|"
    r"\n{2,}|"
    r"(?<=\n)(?=\n)"
)


def split_sentences(text: str) -> List[str]:
    parts = [segment.strip() for segment in SENTENCE_SPLIT_PATTERN.split(text) if segment.strip()]
    return parts if parts else ([text.strip()] if text.strip() else [])


def split_sentences_with_spans(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cursor = 0
    for sentence in split_sentences(text):
        start = text.find(sentence, cursor)
        if start < 0:
            start = text.find(sentence)
        if start < 0:
            continue
        end = start + len(sentence)
        rows.append({"index": len(rows), "text": sentence, "start": start, "end": end})
        cursor = end
    return rows


def build_keyword_contexts(text: str, keyword: str) -> List[Dict[str, Any]]:
    sentences = split_sentences(text)
    contexts: List[Dict[str, Any]] = []
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        return contexts

    for index, sentence in enumerate(sentences):
        if normalized_keyword in sentence:
            contexts.append(
                {
                    "index": index,
                    "previous": sentences[index - 1] if index > 0 else "",
                    "current": sentence,
                    "next": sentences[index + 1] if index + 1 < len(sentences) else "",
                    "keyword": normalized_keyword,
                }
            )
    return contexts


def build_domain_profile_rows(
    tokens: List[Dict[str, Any]],
    categories: Dict[str, Dict[str, str]],
    language: str = "en",
) -> List[Dict[str, Any]]:
    total = max(len(tokens), 1)
    domain_counter: Counter[str] = Counter()
    lemma_by_domain: Dict[str, set[str]] = {}
    for item in tokens:
        raw_codes = item.get("domain_codes", [])
        codes: List[str] = []
        if isinstance(raw_codes, list):
            codes = [str(c).strip() for c in raw_codes if str(c).strip()]
        if not codes:
            fallback = str(item.get("domain_code", "")).strip()
            if fallback:
                codes = [fallback]
        lemma = str(item.get("lemma", "")).strip()
        if not codes or not lemma:
            continue
        for code in codes:
            domain_counter[code] += 1
            lemma_by_domain.setdefault(code, set()).add(lemma)

    rows: List[Dict[str, Any]] = []
    for domain_code, count in sorted(domain_counter.items(), key=lambda pair: (-pair[1], pair[0])):
        info = categories.get(domain_code, {})
        if isinstance(info, dict):
            label = localize_category_label(categories, domain_code, language)
            description = info.get("en", label)
        else:
            label = domain_code
            description = domain_code
        rows.append(
            {
                "domain_code": domain_code,
                "domain_label": label,
                "description": description,
                "frequency": count,
                "relative_per_10k": round(count * 10000 / total, 2),
                "token_ratio": round(count * 100 / total, 2),
                "types": len(lemma_by_domain.get(domain_code, set())),
                "tokens": count,
            }
        )
    return rows


def build_domain_word_rows(tokens: List[Dict[str, Any]], domain_code: str) -> List[Dict[str, Any]]:
    normalized_domain = domain_code.strip()
    if not normalized_domain:
        return []

    total = max(len(tokens), 1)
    rows: Dict[str, Dict[str, Any]] = {}
    for item in tokens:
        raw_codes = item.get("domain_codes", [])
        codes: List[str] = []
        if isinstance(raw_codes, list):
            codes = [str(c).strip() for c in raw_codes if str(c).strip()]
        if not codes:
            fallback = str(item.get("domain_code", "")).strip()
            if fallback:
                codes = [fallback]
        if normalized_domain not in codes:
            continue
        lemma = str(item.get("lemma", "")).strip()
        surface = str(item.get("surface", "")).strip() or lemma
        if not lemma:
            continue
        bucket = rows.setdefault(
            lemma,
            {
                "word": surface,
                "lemma": lemma,
                "frequency": 0,
                "relative_per_10k": 0.0,
                "concordance": 0,
            },
        )
        bucket["frequency"] += 1
        bucket["concordance"] += 1
        # Keep a stable visible form: prefer shorter common surface.
        if len(surface) < len(str(bucket["word"])):
            bucket["word"] = surface

    sorted_rows = sorted(rows.values(), key=lambda item: (-int(item["frequency"]), str(item["lemma"])))
    for row in sorted_rows:
        row["relative_per_10k"] = round(float(row["frequency"]) * 10000 / total, 2)
    return sorted_rows


def build_kwic_rows(
    text: str,
    tokens: List[Dict[str, Any]],
    keyword: str,
    domain_code: str = "",
    pos_filter: str = "",
    use_regex: bool = False,
    span: int = 36,
) -> List[Dict[str, Any]]:
    normalized_keyword = keyword.strip()
    normalized_domain = domain_code.strip()
    if not text.strip() or not normalized_keyword:
        return []

    pos_set = {p.strip() for p in str(pos_filter or "").split(",") if p.strip()}
    rx = None
    if use_regex:
        try:
            rx = re.compile(normalized_keyword)
        except re.error:
            return []

    sentence_rows = split_sentences_with_spans(text)
    if not sentence_rows:
        return []

    sentence_starts = [int(r["start"]) for r in sentence_rows]

    def sentence_index_for_offset(offset: int) -> int:
        if not sentence_rows:
            return 0
        idx = bisect_right(sentence_starts, offset) - 1
        if idx < 0:
            idx = 0
        while idx < len(sentence_rows) and offset >= int(sentence_rows[idx]["end"]):
            idx += 1
        return min(idx, len(sentence_rows) - 1)

    kwic_rows: List[Dict[str, Any]] = []
    cursor = 0

    for token in tokens:
        lemma = str(token.get("lemma", "")).strip()
        surface = str(token.get("surface", "")).strip()
        pos = str(token.get("pos", "")).strip()
        token_domain = str(token.get("domain_code", "")).strip()
        raw_codes = token.get("domain_codes", [])
        token_domains: List[str] = []
        if isinstance(raw_codes, list):
            token_domains = [str(c).strip() for c in raw_codes if str(c).strip()]
        if not token_domains and token_domain:
            token_domains = [token_domain]
        if pos_set and pos not in pos_set:
            continue
        if rx is not None:
            if not (rx.search(lemma) or rx.search(surface)):
                continue
        else:
            if "|" in normalized_keyword:
                opts = [x.strip() for x in normalized_keyword.split("|") if x.strip()]
                if lemma not in opts and surface not in opts:
                    continue
            else:
                if lemma != normalized_keyword and surface != normalized_keyword:
                    continue
        if normalized_domain and normalized_domain not in token_domains:
            continue

        candidate = surface or lemma
        if not candidate:
            continue
        offset_raw = token.get("offset", None)
        offset = -1
        if isinstance(offset_raw, int):
            offset = offset_raw
        else:
            try:
                offset = int(offset_raw)
            except Exception:
                offset = -1
        if offset < 0:
            offset = text.find(candidate, cursor)
            if offset < 0:
                offset = text.find(candidate)
            if offset < 0:
                continue
        cursor = max(cursor, offset + len(candidate))

        sentence_index = sentence_index_for_offset(offset)

        sentence = sentence_rows[sentence_index]["text"]
        sentence_start = int(sentence_rows[sentence_index]["start"])
        local_offset = max(0, offset - sentence_start)
        left_slice_start = max(0, local_offset - span)
        right_slice_end = min(len(sentence), local_offset + len(candidate) + span)
        left_context = sentence[left_slice_start:local_offset]
        right_context = sentence[local_offset + len(candidate):right_slice_end]

        kwic_rows.append(
            {
                "line": len(kwic_rows) + 1,
                "left": left_context,
                "key": candidate,
                "right": right_context,
                "domain_code": token_domain,
                "domain_codes": token_domains,
                "source_offset": offset,
                "sentence_index": sentence_index,
                "previous": sentence_rows[sentence_index - 1]["text"] if sentence_index > 0 else "",
                "current": sentence,
                "next": sentence_rows[sentence_index + 1]["text"] if sentence_index + 1 < len(sentence_rows) else "",
                "confidence": 1.0 if lemma == normalized_keyword else 0.85,
            }
        )

    return kwic_rows


def build_context_detail(text: str, source_offset: int, key: str, window: int = 140) -> Dict[str, Any]:
    start = max(0, source_offset - window)
    end = min(len(text), source_offset + max(len(key), 1) + window)
    snippet = text[start:end]
    local = max(0, source_offset - start)
    return {
        "snippet": snippet,
        "highlight_start": local,
        "highlight_end": local + max(len(key), 1),
        "start": start,
        "end": end,
    }
