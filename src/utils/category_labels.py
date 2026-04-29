from __future__ import annotations

import re
from typing import Dict


_ZH_GLOSSARY = {
    "GENERAL AND ABSTRACT TERMS": "\u4e00\u822c\u4e0e\u62bd\u8c61\u672f\u8bed",
    "General": "\u4e00\u822c",
    "actions": "\u884c\u4e3a",
    "action": "\u884c\u4e3a",
    "states": "\u72b6\u6001",
    "state": "\u72b6\u6001",
    "processes": "\u8fc7\u7a0b",
    "process": "\u8fc7\u7a0b",
    "Time": "\u65f6\u95f4",
    "Language": "\u8bed\u8a00",
    "Speech": "\u8a00\u8bed",
    "communication": "\u4ea4\u6d41",
    "Food": "\u98df\u7269",
    "Drinks": "\u996e\u54c1",
    "Health": "\u5065\u5eb7",
    "disease": "\u75be\u75c5",
    "Emotion": "\u60c5\u7eea",
    "EMOTIONAL": "\u60c5\u7eea",
    "Government": "\u653f\u5e9c",
    "Politics": "\u653f\u6cbb",
    "Business": "\u5546\u4e1a",
    "Money": "\u91d1\u94b1",
    "Work": "\u5de5\u4f5c",
    "Education": "\u6559\u80b2",
    "Science": "\u79d1\u5b66",
    "technology": "\u6280\u672f",
    "People": "\u4eba\u7fa4",
    "Relationship": "\u5173\u7cfb",
    "Religion": "\u5b97\u6559",
    "Sports": "\u4f53\u80b2",
    "Games": "\u6e38\u620f",
    "Music": "\u97f3\u4e50",
    "Arts": "\u827a\u672f",
    "Compare": "\u6bd4\u8f83",
    "Measurement": "\u6d4b\u91cf",
    "Weather": "\u5929\u6c14",
    "Light": "\u5149",
    "domain": "\u8bed\u4e49\u57df",
    "Unmatched": "\u672a\u5339\u914d",
    "Negative": "\u5426\u5b9a",
    "Pronouns": "\u4ee3\u8bcd",
    "TV": "\u7535\u89c6",
    "Radio": "\u5e7f\u64ad",
    "Cinema": "\u7535\u5f71",
}

_JA_GLOSSARY = {
    "GENERAL AND ABSTRACT TERMS": "\u4e00\u822c\u30fb\u62bd\u8c61\u8a9e",
    "General": "\u4e00\u822c",
    "actions": "\u884c\u70ba",
    "action": "\u884c\u70ba",
    "states": "\u72b6\u614b",
    "state": "\u72b6\u614b",
    "processes": "\u904e\u7a0b",
    "process": "\u904e\u7a0b",
    "Time": "\u6642\u9593",
    "Language": "\u8a00\u8a9e",
    "Speech": "\u767a\u8a71",
    "communication": "\u30b3\u30df\u30e5\u30cb\u30b1\u30fc\u30b7\u30e7\u30f3",
    "Food": "\u98df\u3079\u7269",
    "Drinks": "\u98f2\u307f\u7269",
    "Health": "\u5065\u5eb7",
    "disease": "\u75c5\u6c17",
    "Emotion": "\u611f\u60c5",
    "EMOTIONAL": "\u611f\u60c5",
    "Government": "\u653f\u5e9c",
    "Politics": "\u653f\u6cbb",
    "Business": "\u30d3\u30b8\u30cd\u30b9",
    "Money": "\u304a\u91d1",
    "Work": "\u4ed5\u4e8b",
    "Education": "\u6559\u80b2",
    "Science": "\u79d1\u5b66",
    "technology": "\u6280\u8853",
    "People": "\u4eba",
    "Relationship": "\u95a2\u4fc2",
    "Religion": "\u5b97\u6559",
    "Sports": "\u30b9\u30dd\u30fc\u30c4",
    "Games": "\u30b2\u30fc\u30e0",
    "Music": "\u97f3\u697d",
    "Arts": "\u82b8\u8853",
    "Compare": "\u6bd4\u8f03",
    "Measurement": "\u8a08\u6e2c",
    "Weather": "\u5929\u6c17",
    "Light": "\u5149",
    "domain": "\u9818\u57df",
    "Unmatched": "\u672a\u4e00\u81f4",
    "Negative": "\u5426\u5b9a",
    "Pronouns": "\u4ee3\u540d\u8a5e",
    "TV": "\u30c6\u30ec\u30d3",
    "Radio": "\u30e9\u30b8\u30aa",
    "Cinema": "\u6620\u753b",
}


def _apply_glossary(label_en: str, glossary: Dict[str, str]) -> str:
    out = str(label_en or "")
    for src in sorted(glossary.keys(), key=len, reverse=True):
        out = out.replace(src, glossary[src])
    return out


_ASCII_WORD = re.compile(r"[A-Za-z]{2,}")


def localize_category_label(categories: Dict[str, Dict[str, str]], domain_code: str, language: str) -> str:
    info = categories.get(domain_code, {})
    if not isinstance(info, dict):
        return domain_code
    if language == "en":
        return info.get("en", domain_code)
    if language in ("zh", "ja") and info.get(language):
        return str(info[language])
    label_en = str(info.get("en", domain_code))
    if language == "zh":
        out = _apply_glossary(label_en, _ZH_GLOSSARY)
        return domain_code if _ASCII_WORD.search(out) else out
    if language == "ja":
        out = _apply_glossary(label_en, _JA_GLOSSARY)
        return domain_code if _ASCII_WORD.search(out) else out
    return label_en


def localize_categories(categories: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for code, info in categories.items():
        if not isinstance(info, dict):
            out[code] = {"en": code, "zh": code, "ja": code}
            continue
        en = str(info.get("en", code))
        out[code] = {
            "en": en,
            "zh": str(info.get("zh") or localize_category_label(categories, code, "zh")),
            "ja": str(info.get("ja") or localize_category_label(categories, code, "ja")),
        }
    return out
