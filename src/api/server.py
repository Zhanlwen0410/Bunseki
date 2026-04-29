"""Local HTTP API for the Electron desktop (session mirrors WebviewAPI)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

# Repo root (wmatrix_ja/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# -- configurable limits ------------------------------------------------------
_MAX_TEXT_LENGTH = int(os.environ.get("BUNSEKI_MAX_TEXT_LENGTH", "1000000"))

from src.analysis.compare import build_comparison
from src.analysis.context import build_context_detail, build_domain_profile_rows, build_domain_word_rows
from src.main import default_lexicon_path, clear_tagger_cache
from src.services.analysis_service import (
    acquire_lexicon_lock,
    analyze_with_profile,
    append_lexicon_terms,
    kwic_from_result,
    lexicon_overview_payload,
    parse_min_frequency,
    parse_top_n,
    validate_analyze_options,
)
from src.utils.category_labels import localize_categories
from src.utils.file_io import read_json_file
from src.utils.file_io import write_json


# NOTE: This server is designed for single-user desktop use.
# `state` is a module-level singleton — only one analysis session exists at a time.
class ApiState:
    def __init__(self) -> None:
        self.base_dir = _REPO_ROOT
        self.data_dir = self.base_dir / "data"
        self.categories_path = self.data_dir / "usas_categories.json"
        self.lexicon_path = Path(default_lexicon_path())
        self.categories: dict[str, Any] = read_json_file(str(self.categories_path))
        self.last_result: dict[str, Any] | None = None


state = ApiState()
app = FastAPI(title="Bunseki Local API", version="1.0")

def _allow_localhost_origin(origin: str | None) -> bool:
    if origin is None:
        return False
    return origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:")


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost):\d+$",
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/assets/cc-by-nc-nd.svg")
def cc_by_nc_nd_svg() -> FileResponse:
    icon_path = state.base_dir / "image" / "by-nc-nd.svg"
    return FileResponse(path=str(icon_path), media_type="image/svg+xml", filename="by-nc-nd.svg")


@app.post("/reset-session")
def reset_session() -> dict[str, Any]:
    state.last_result = None
    return {"ok": True}


@app.get("/bootstrap")
def bootstrap() -> dict[str, Any]:
    sample_text = ""
    sample_path = state.base_dir / "sample.txt"
    if sample_path.exists():
        sample_text = sample_path.read_text(encoding="utf-8")
    return {
        "sample_text": sample_text,
        "lexicon_path": str(state.lexicon_path),
        "categories": localize_categories(state.categories),
        "about": {
            "license": "CC-BY-NC-ND 4.0",
            "organization": "School of Foreign Languages, Xinjiang University",
            "author": "Zhang Wenze",
            "cc_icon_url": "/assets/cc-by-nc-nd.svg",
        },
        "help": (
            "WLSP is now used as the original lexicon source. "
            "Mapping prefers koumoku1 overrides, then falls back to top-level WLSP classes. "
            "Lexicon import normalizes entries and tries lemma-first matching."
        ),
    }


class AnalyzeRequest(BaseModel):
    text: str = ""
    language: str = "zh"
    tokenizer: str = "sudachi"
    mode: str = "C"
    min_frequency: Any = 1
    top_n: Any = None
    lexicon_path: Optional[str] = None


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict[str, Any]:
    text = str(req.text or "").strip()
    if not text:
        return {
            "ok": False,
            "error": {
                "code": "missing_text",
                "message": "Text is required.",
                "hint": "Paste or type Japanese text in the input area.",
            },
        }
    if len(text) > _MAX_TEXT_LENGTH:
        return {
            "ok": False,
            "error": {
                "code": "text_too_large",
                "message": f"Text exceeds {_MAX_TEXT_LENGTH} character limit.",
                "hint": "Split the text into smaller segments.",
            },
        }
    language = str(req.language or "zh").strip()
    tokenizer = str(req.tokenizer or "sudachi").strip()
    mode = str(req.mode or "C").strip()
    try:
        min_frequency = parse_min_frequency(req.min_frequency)
        top_n = parse_top_n(req.top_n)
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "error": {
                "code": "invalid_number",
                "message": f"Invalid numeric option: {exc}",
                "hint": "min_frequency and top_n must be integers.",
            },
        }

    err = validate_analyze_options(
        language=language,
        tokenizer=tokenizer,
        mode=mode,
        min_frequency=min_frequency,
        top_n=top_n,
    )
    if err:
        return {"ok": False, "error": err}

    lexicon = str(req.lexicon_path or state.lexicon_path).strip()
    if not lexicon:
        return {
            "ok": False,
            "error": {
                "code": "missing_lexicon",
                "message": "Lexicon path is empty.",
                "hint": "Set a valid lexicon JSON path.",
            },
        }

    try:
        data = analyze_with_profile(
            text=text,
            lexicon_path=lexicon,
            categories_path=str(state.categories_path),
            categories=state.categories,
            language=language,
            tokenizer=tokenizer,
            mode=mode,
            unknown_domain="Z99",
            min_frequency=min_frequency,
            top_n=top_n,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": {
                "code": "analyze_failed",
                "message": str(exc),
                "hint": "Check lexicon/categories paths and tokenizer installation (SudachiPy or MeCab).",
            },
        }

    state.last_result = data["result"]
    # Keep lexicon center aligned with the path used for analysis.
    state.lexicon_path = Path(lexicon)
    return {"ok": True, "result": data["result"], "profile": data["profile"]}


@app.get("/domain-profile")
def domain_profile(language: str = "ja") -> dict[str, Any]:
    if not state.last_result:
        return {
            "ok": False,
            "error": {
                "code": "no_session",
                "message": "No analysis result yet.",
                "hint": "Run Analyze first.",
            },
        }
    profile = build_domain_profile_rows(
        state.last_result["tokens"],
        state.categories,
        language=language,
    )
    return {"ok": True, "profile": profile}


@app.get("/domain-words/{domain_code}")
def domain_words(domain_code: str) -> list[dict[str, Any]]:
    if not state.last_result:
        return []
    return build_domain_word_rows(state.last_result["tokens"], domain_code)


class KwicRequest(BaseModel):
    keyword: str = ""
    domain_code: str = ""
    pos_filter: str = ""
    use_regex: bool = False


class WordFrequencyRequest(BaseModel):
    form: str = "lemma"  # lemma|surface
    pos_filter: str = ""
    top_n: int = 50


@app.post("/word-frequency")
def word_frequency(req: WordFrequencyRequest) -> dict[str, Any]:
    if not state.last_result:
        return {"ok": False, "error": {"code": "no_session", "message": "No analysis result yet.", "hint": "Run Analyze first."}}
    form = str(req.form or "lemma").strip().lower()
    if form not in ("lemma", "surface"):
        return {"ok": False, "error": {"code": "invalid_form", "message": "form must be lemma or surface.", "hint": ""}}
    top_n = int(req.top_n or 50)
    top_n = max(1, min(top_n, 500))
    pos_set = {p.strip() for p in str(req.pos_filter or "").split(",") if p.strip()}

    freq: dict[str, int] = {}
    for tok in state.last_result.get("tokens", []):
        pos = str(tok.get("pos", "")).strip()
        if pos_set and pos not in pos_set:
            continue
        raw = tok.get("lemma") if form == "lemma" else tok.get("surface")
        term = str(raw or "").strip()
        if not term:
            continue
        freq[term] = int(freq.get(term, 0)) + 1
    rows = [{"term": k, "count": v} for k, v in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]
    return {"ok": True, "rows": rows}


@app.post("/kwic")
def kwic(req: KwicRequest) -> list[dict[str, Any]]:
    if not state.last_result:
        return []
    return kwic_from_result(
        state.last_result,
        keyword=str(req.keyword or ""),
        domain_code=str(req.domain_code or ""),
        pos_filter=str(req.pos_filter or ""),
        use_regex=bool(req.use_regex),
        span=36,
    )


class ContextDetailRequest(BaseModel):
    offset: int = Field(..., ge=0)
    key: str = ""


@app.post("/context-detail")
def context_detail(req: ContextDetailRequest) -> dict[str, Any]:
    if not state.last_result:
        return {"error": {"code": "no_session", "message": "No analysis result yet.", "hint": ""}}
    src = state.last_result.get("source_text", "")
    off = int(req.offset)
    if off > len(src):
        return {
            "error": {
                "code": "offset_out_of_range",
                "message": "offset is outside the source text.",
                "hint": "",
            }
        }
    return build_context_detail(src, off, req.key, window=180)


@app.get("/lexicon/overview")
def lexicon_overview(language: str = "en") -> dict[str, Any]:
    return lexicon_overview_payload(state.lexicon_path, state.categories, language=language)


@app.get("/lexicon/raw")
def lexicon_raw() -> dict[str, Any]:
    return read_json_file(str(state.lexicon_path))


class LexiconAddRequest(BaseModel):
    items: list[dict[str, str]] = Field(default_factory=list)


@app.post("/lexicon/add")
def lexicon_add(req: LexiconAddRequest) -> dict[str, Any]:
    if not isinstance(req.items, list):
        return {
            "ok": False,
            "error": {
                "code": "invalid_payload",
                "message": "items must be a list of objects.",
                "hint": "Send [{domain_code, lemma}, ...].",
            },
        }
    known = set(state.categories.keys()) if isinstance(state.categories, dict) else None
    try:
        summary = append_lexicon_terms(
            state.lexicon_path,
            req.items,
            known_domain_codes=known,
            default_domain="Z99",
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": {
                "code": "lexicon_write_failed",
                "message": str(exc),
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


class LexiconRemoveTermRequest(BaseModel):
    domain_code: str
    lemma: str


@app.post("/lexicon/remove-term")
def lexicon_remove_term(req: LexiconRemoveTermRequest) -> dict[str, Any]:
    domain_code = str(req.domain_code or "").strip()
    lemma = str(req.lemma or "").strip()
    if not domain_code or not lemma:
        return {"ok": False, "error": {"code": "invalid_payload", "message": "domain_code and lemma are required.", "hint": ""}}
    try:
        with acquire_lexicon_lock():
            lexicon = read_json_file(str(state.lexicon_path))
            words = list(lexicon.get(domain_code, []))
            before = len(words)
            words = [w for w in words if str(w).strip() != lemma]
            removed = before - len(words)
            if words:
                lexicon[domain_code] = words
            elif domain_code in lexicon:
                del lexicon[domain_code]
            write_json(lexicon, state.lexicon_path)
        clear_tagger_cache()
        return {"ok": True, "removed": removed}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": {"code": "lexicon_write_failed", "message": str(exc), "hint": ""}}


class LexiconRemoveDomainRequest(BaseModel):
    domain_code: str


@app.post("/lexicon/remove-domain")
def lexicon_remove_domain(req: LexiconRemoveDomainRequest) -> dict[str, Any]:
    domain_code = str(req.domain_code or "").strip()
    if not domain_code:
        return {"ok": False, "error": {"code": "invalid_payload", "message": "domain_code is required.", "hint": ""}}
    try:
        with acquire_lexicon_lock():
            lexicon = read_json_file(str(state.lexicon_path))
            existed = domain_code in lexicon
            if existed:
                del lexicon[domain_code]
                write_json(lexicon, state.lexicon_path)
        if existed:
            clear_tagger_cache()
        return {"ok": True, "removed": 1 if existed else 0}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": {"code": "lexicon_write_failed", "message": str(exc), "hint": ""}}


class LexiconMoveTermRequest(BaseModel):
    from_domain: str
    to_domain: str
    lemma: str


@app.post("/lexicon/move-term")
def lexicon_move_term(req: LexiconMoveTermRequest) -> dict[str, Any]:
    from_domain = str(req.from_domain or "").strip()
    to_domain = str(req.to_domain or "").strip()
    lemma = str(req.lemma or "").strip()
    if not from_domain or not to_domain or not lemma:
        return {"ok": False, "error": {"code": "invalid_payload", "message": "from_domain, to_domain and lemma are required.", "hint": ""}}
    try:
        with acquire_lexicon_lock():
            lexicon = read_json_file(str(state.lexicon_path))
            src_words = [w for w in list(lexicon.get(from_domain, [])) if str(w).strip() != lemma]
            lexicon[from_domain] = src_words
            if not src_words and from_domain in lexicon:
                del lexicon[from_domain]
            lexicon.setdefault(to_domain, [])
            if lemma not in lexicon[to_domain]:
                lexicon[to_domain].append(lemma)
            write_json(lexicon, state.lexicon_path)
        clear_tagger_cache()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": {"code": "lexicon_write_failed", "message": str(exc), "hint": ""}}


class CompareRequest(BaseModel):
    left_text: str = ""
    right_text: str = ""
    language: str = "ja"
    mode: str = "C"
    min_frequency: Any = 1
    top_n: Any = None
    lexicon_path: Optional[str] = None


@app.post("/compare")
def compare(req: CompareRequest) -> dict[str, Any]:
    left = str(req.left_text or "").strip()
    right = str(req.right_text or "").strip()
    if not left or not right:
        return {
            "ok": False,
            "error": {
                "code": "missing_text",
                "message": "Both left_text and right_text are required.",
                "hint": "",
            },
        }
    limit = _MAX_TEXT_LENGTH
    if len(left) > limit or len(right) > limit:
        return {
            "ok": False,
            "error": {
                "code": "text_too_large",
                "message": f"Text exceeds {limit} character limit.",
                "hint": "Split the text into smaller segments.",
            },
        }
    language = str(req.language or "ja").strip()
    mode = str(req.mode or "C").strip()
    try:
        min_frequency = parse_min_frequency(req.min_frequency)
        top_n = parse_top_n(req.top_n)
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "error": {
                "code": "invalid_number",
                "message": str(exc),
                "hint": "",
            },
        }
    err = validate_analyze_options(
        language=language,
        mode=mode,
        min_frequency=min_frequency,
        top_n=top_n,
    )
    if err:
        return {"ok": False, "error": err}
    lexicon = str(req.lexicon_path or state.lexicon_path).strip()
    try:
        left_data = analyze_with_profile(
            text=left,
            lexicon_path=lexicon,
            categories_path=str(state.categories_path),
            categories=state.categories,
            language=language,
            mode=mode,
            unknown_domain="Z99",
            min_frequency=min_frequency,
            top_n=top_n,
            include_profile=False,
        )
        right_data = analyze_with_profile(
            text=right,
            lexicon_path=lexicon,
            categories_path=str(state.categories_path),
            categories=state.categories,
            language=language,
            mode=mode,
            unknown_domain="Z99",
            min_frequency=min_frequency,
            top_n=top_n,
            include_profile=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": {
                "code": "compare_failed",
                "message": str(exc),
                "hint": "",
            },
        }
    lr = left_data["result"]
    rr = right_data["result"]
    return {"ok": True, "comparison": build_comparison(lr, rr)}
