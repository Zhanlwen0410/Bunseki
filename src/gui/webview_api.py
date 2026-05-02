from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.analysis.context import build_context_detail, build_domain_word_rows
from src.services.analysis_service import (
    analyze_with_profile,
    append_lexicon_terms,
    kwic_from_result,
    lexicon_overview_payload,
    parse_analyze_params,
    safe_error_msg,
)
from src.main import default_lexicon_path
from src.utils.file_io import read_json_file


class WebviewAPI:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.data_dir = base_dir / "data"
        self.categories_path = self.data_dir / "usas_categories.json"
        self.lexicon_path = Path(default_lexicon_path())
        self.categories = read_json_file(str(self.categories_path))
        self.last_result: dict[str, Any] | None = None

    def bootstrap(self) -> dict[str, Any]:
        sample_text = ""
        sample_path = self.base_dir / "sample.txt"
        if sample_path.exists():
            sample_text = sample_path.read_text(encoding="utf-8")
        return {
            "sample_text": sample_text,
            "lexicon_path": str(self.lexicon_path),
            "categories": self.categories,
            "help": (
                "WordNet is used as the primary semantic source. "
                "Pipeline uses WordNet->USAS mapping first, then vector nearest-neighbor fallback."
            ),
        }

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        parsed = parse_analyze_params(
            text_raw=payload.get("text", ""),
            language_raw=payload.get("language", "zh"),
            tokenizer_raw=payload.get("tokenizer", "sudachi"),
            mode_raw=payload.get("mode", "C"),
            min_frequency_raw=payload.get("min_frequency", 1),
            top_n_raw=payload.get("top_n"),
            lexicon_path_raw=payload.get("lexicon_path"),
            default_lexicon_path=str(self.lexicon_path),
            use_bert_wsd_raw=payload.get("use_bert_wsd", True),
            bert_model_dir_raw=payload.get("bert_model_dir"),
        )
        if not parsed.get("ok"):
            return {"ok": False, "error": parsed["error"]}

        try:
            data = analyze_with_profile(
                text=parsed["text"],
                lexicon_path=parsed["lexicon"],
                categories_path=str(self.categories_path),
                categories=self.categories,
                language=parsed["language"],
                tokenizer=parsed["tokenizer"],
                mode=parsed["mode"],
                unknown_domain="Z99",
                min_frequency=parsed["min_frequency"],
                top_n=parsed["top_n"],
                use_bert_wsd=parsed["use_bert_wsd"],
                bert_model_dir=parsed["bert_model_dir"],
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": {
                    "code": "analyze_failed",
                    "message": safe_error_msg(exc),
                    "hint": "Check lexicon/categories paths and Sudachi installation.",
                },
            }

        self.last_result = data["result"]
        return {"ok": True, "result": data["result"], "profile": data["profile"]}

    def domain_words(self, domain_code: str) -> list[dict[str, Any]]:
        if not self.last_result:
            return []
        return build_domain_word_rows(self.last_result["tokens"], domain_code)

    def kwic(self, keyword: str, domain_code: str = "") -> list[dict[str, Any]]:
        if not self.last_result:
            return []
        return kwic_from_result(
            self.last_result,
            keyword=keyword,
            domain_code=domain_code,
            span=36,
        )

    def context_detail(self, offset: int, key: str) -> dict[str, Any]:
        if not self.last_result:
            return {}
        try:
            off = int(offset)
        except (TypeError, ValueError):
            return {
                "error": {
                    "code": "invalid_offset",
                    "message": "offset must be an integer.",
                    "hint": "",
                }
            }
        if off < 0 or off >= len(self.last_result.get("source_text", "")):
            return {
                "error": {
                    "code": "offset_out_of_range",
                    "message": "offset is outside the source text.",
                    "hint": "",
                }
            }
        return build_context_detail(self.last_result["source_text"], off, key, window=180)

    def lexicon_overview(self) -> dict[str, Any]:
        return lexicon_overview_payload(self.lexicon_path, self.categories)

    def add_lexicon_terms(self, items: list[dict[str, str]]) -> dict[str, Any]:
        if not isinstance(items, list):
            return {
                "ok": False,
                "error": {
                    "code": "invalid_payload",
                    "message": "items must be a list of objects.",
                    "hint": "Send [{domain_code, lemma}, ...].",
                },
            }
        known = set(self.categories.keys()) if isinstance(self.categories, dict) else None
        try:
            summary = append_lexicon_terms(
                self.lexicon_path,
                items,
                known_domain_codes=known,
                default_domain="Z99",
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": {
                    "code": "lexicon_write_failed",
                    "message": safe_error_msg(exc),
                    "hint": "Check file permissions and JSON format.",
                },
            }
        out: dict[str, Any] = {"ok": True, **summary}
        if summary.get("unknown_domain_codes"):
            out["warning"] = (
                "Some domain codes are not in usas_categories.json: "
                + ", ".join(summary["unknown_domain_codes"])
            )
        return out
