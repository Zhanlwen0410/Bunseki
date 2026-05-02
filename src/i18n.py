from __future__ import annotations

from typing import Dict


SUPPORTED_LANGUAGES = ("zh", "ja", "en")


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "app_title": {
        "zh": "Bunseki",
        "ja": "Bunseki",
        "en": "Bunseki",
    },
    "lexicon": {"zh": "\u8bcd\u5178", "ja": "\u8f9e\u66f8", "en": "Lexicon"},
    "browse": {"zh": "\u6d4f\u89c8", "ja": "\u53c2\u7167", "en": "Browse"},
    "mode": {"zh": "\u6a21\u5f0f", "ja": "\u30e2\u30fc\u30c9", "en": "Mode"},
    "min_freq": {"zh": "\u6700\u5c0f\u9891\u6b21", "ja": "\u6700\u5c0f\u983b\u5ea6", "en": "Min Freq"},
    "top_n": {"zh": "\u524dN\u9879", "ja": "\u4e0a\u4f4dN\u4ef6", "en": "Top N"},
    "unknown": {"zh": "\u672a\u5339\u914d\u6807\u7b7e", "ja": "\u672a\u4e00\u81f4\u30e9\u30d9\u30eb", "en": "Unknown"},
    "language": {"zh": "\u754c\u9762\u8bed\u8a00", "ja": "\u8868\u793a\u8a00\u8a9e", "en": "Language"},
    "open_txt": {"zh": "\u6253\u5f00\u6587\u672c", "ja": "\u30c6\u30ad\u30b9\u30c8\u3092\u958b\u304f", "en": "Open TXT"},
    "analyze": {"zh": "\u5206\u6790", "ja": "\u5206\u6790", "en": "Analyze"},
    "export_json": {"zh": "\u5bfc\u51faJSON", "ja": "JSON\u51fa\u529b", "en": "Export JSON"},
    "export_csv": {"zh": "\u5bfc\u51faCSV", "ja": "CSV\u51fa\u529b", "en": "Export CSV"},
    "export_bundle": {"zh": "\u5bfc\u51fa\u5168\u96c6", "ja": "\u4e00\u62ec\u51fa\u529b", "en": "Export Bundle"},
    "clear": {"zh": "\u6e05\u7a7a", "ja": "\u30af\u30ea\u30a2", "en": "Clear"},
    "edit_lexicon": {"zh": "\u8bcd\u5178\u7f16\u8f91\u5668", "ja": "\u8f9e\u66f8\u30a8\u30c7\u30a3\u30bf", "en": "Lexicon Editor"},
    "compare": {"zh": "\u53cc\u6587\u672c\u6bd4\u8f83", "ja": "\u4e8c\u6587\u6bd4\u8f03", "en": "Compare"},
    "keyword_context": {"zh": "\u524d\u540e\u53e5\u5171\u73b0", "ja": "\u524d\u5f8c\u6587\u5171\u8d77", "en": "Keyword Context"},
    "input_text": {"zh": "\u8f93\u5165\u6587\u672c", "ja": "\u5165\u529b\u30c6\u30ad\u30b9\u30c8", "en": "Input Text"},
    "left_text": {"zh": "\u6587\u672cA", "ja": "\u30c6\u30ad\u30b9\u30c8A", "en": "Text A"},
    "right_text": {"zh": "\u6587\u672cB", "ja": "\u30c6\u30ad\u30b9\u30c8B", "en": "Text B"},
    "analysis_result": {"zh": "\u5206\u6790\u7ed3\u679c", "ja": "\u5206\u6790\u7d50\u679c", "en": "Analysis Result"},
    "tokens": {"zh": "\u8bcd\u5143", "ja": "\u30c8\u30fc\u30af\u30f3", "en": "Tokens"},
    "lemma_frequency": {"zh": "\u539f\u5f62\u9891\u6b21", "ja": "\u539f\u5f62\u983b\u5ea6", "en": "Lemma Frequency"},
    "domain_frequency": {"zh": "\u8bed\u4e49\u57df\u9891\u6b21", "ja": "\u610f\u5473\u9818\u57df\u983b\u5ea6", "en": "Domain Frequency"},
    "json_preview": {"zh": "JSON\u9884\u89c8", "ja": "JSON\u30d7\u30ec\u30d3\u30e5\u30fc", "en": "JSON Preview"},
    "recent_files": {"zh": "\u6700\u8fd1\u6587\u4ef6", "ja": "\u6700\u8fd1\u306e\u30d5\u30a1\u30a4\u30eb", "en": "Recent Files"},
    "domain_code": {"zh": "\u57df\u4ee3\u7801", "ja": "\u9818\u57df\u30b3\u30fc\u30c9", "en": "Domain Code"},
    "domain_label": {"zh": "\u57df\u6807\u7b7e", "ja": "\u9818\u57df\u30e9\u30d9\u30eb", "en": "Domain Label"},
    "surface": {"zh": "\u8bcd\u5f62", "ja": "\u8868\u5c64\u5f62", "en": "Surface"},
    "lemma": {"zh": "\u539f\u5f62", "ja": "\u539f\u5f62", "en": "Lemma"},
    "pos": {"zh": "\u8bcd\u6027", "ja": "\u54c1\u8a5e", "en": "POS"},
    "count": {"zh": "\u9891\u6b21", "ja": "\u983b\u5ea6", "en": "Count"},
    "current_sentence": {"zh": "\u5f53\u524d\u53e5", "ja": "\u73fe\u5728\u6587", "en": "Current"},
    "previous_sentence": {"zh": "\u524d\u53e5", "ja": "\u524d\u6587", "en": "Previous"},
    "next_sentence": {"zh": "\u540e\u53e5", "ja": "\u5f8c\u6587", "en": "Next"},
    "search_keyword": {"zh": "\u68c0\u7d22\u5173\u952e\u8bcd", "ja": "\u30ad\u30fc\u30ef\u30fc\u30c9\u691c\u7d22", "en": "Keyword"},
    "find_context": {"zh": "\u67e5\u627e\u4e0a\u4e0b\u6587", "ja": "\u6587\u8108\u691c\u7d22", "en": "Find Context"},
    "load_left": {"zh": "\u8f7d\u5165A", "ja": "A\u8aad\u8fbc", "en": "Load A"},
    "load_right": {"zh": "\u8f7d\u5165B", "ja": "B\u8aad\u8fbc", "en": "Load B"},
    "compare_lemma": {"zh": "\u8bcd\u9891\u5bf9\u6bd4", "ja": "\u8a9e\u5f59\u6bd4\u8f03", "en": "Lemma Compare"},
    "compare_domain": {"zh": "\u8bed\u4e49\u57df\u5bf9\u6bd4", "ja": "\u9818\u57df\u6bd4\u8f03", "en": "Domain Compare"},
    "add_term": {"zh": "\u6dfb\u52a0\u8bcd\u6761", "ja": "\u8a9e\u5f59\u8ffd\u52a0", "en": "Add Term"},
    "remove_domain": {"zh": "\u5220\u9664\u57df", "ja": "\u9818\u57df\u524a\u9664", "en": "Remove Domain"},
    "save": {"zh": "\u4fdd\u5b58", "ja": "\u4fdd\u5b58", "en": "Save"},
    "save_project": {"zh": "\u4fdd\u5b58\u9879\u76ee", "ja": "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u3092\u4fdd\u5b58", "en": "Save Project"},
    "open_project": {"zh": "\u6253\u5f00\u9879\u76ee", "ja": "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u3092\u958b\u304f", "en": "Open Project"},
    "projects": {"zh": "\u9879\u76ee", "ja": "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8", "en": "Projects"},
    "jump_context": {"zh": "\u8df3\u8f6c\u5230\u4e0a\u4e0b\u6587", "ja": "\u6587\u8108\u3078\u79fb\u52d5", "en": "Jump to Context"},
    "context_detail": {"zh": "\u4e0a\u4e0b\u6587\u8be6\u60c5", "ja": "\u6587\u8108\u8a73\u7d30", "en": "Context Detail"},
    "status_ready": {"zh": "\u5c31\u7eea", "ja": "\u6e96\u5099\u5b8c\u4e86", "en": "Ready"},
    "no_text": {"zh": "\u8bf7\u8f93\u5165\u6216\u8f7d\u5165\u65e5\u8bed\u6587\u672c\u3002", "ja": "\u65e5\u672c\u8a9e\u30c6\u30ad\u30b9\u30c8\u3092\u5165\u529b\u3059\u308b\u304b\u8aad\u307f\u8fbc\u3093\u3067\u304f\u3060\u3055\u3044\u3002", "en": "Please enter or load Japanese text."},
    "no_analysis": {"zh": "\u8bf7\u5148\u6267\u884c\u5206\u6790\u3002", "ja": "\u5148\u306b\u5206\u6790\u3092\u5b9f\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "en": "Please run analysis first."},
    "analysis_failed": {"zh": "\u5206\u6790\u5931\u8d25", "ja": "\u5206\u6790\u5931\u6557", "en": "Analysis failed"},
    "open_failed": {"zh": "\u6253\u5f00\u5931\u8d25", "ja": "\u8aad\u8fbc\u5931\u6557", "en": "Open Failed"},
    "export_failed": {"zh": "\u5bfc\u51fa\u5931\u8d25", "ja": "\u51fa\u529b\u5931\u6557", "en": "Export Failed"},
    "select_domain_prompt": {"zh": "\u8bf7\u8f93\u5165\u76ee\u6807\u57df\u4ee3\u7801\uff08\u5982A1\u3001E4.1\uff09\uff1a", "ja": "\u79fb\u52d5\u5148\u306e\u9818\u57df\u30b3\u30fc\u30c9\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\uff08\u4f8b\uff1aA1\u3001E4.1\uff09\uff1a", "en": "Enter target domain code (e.g. A1, E4.1):"}
}


def tr(lang: str, key: str) -> str:
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"
    entry = TRANSLATIONS.get(key, {})
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key
