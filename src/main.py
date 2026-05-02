from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import is_llm_available, load_usas_labels_ja
from src.preprocessing.tokenizer import BaseTokenizer, create_tokenizer
from src.semantic.tagger import SemanticTagger

# Process-local caches avoid reloading tokenizers + large lexicons on every analyze/KWIC pass.
_cache_lock = threading.RLock()
_tokenizer_cache: dict[tuple[str, str], BaseTokenizer] = {}
_tagger_cache: dict[tuple[str, str, str, str], SemanticTagger] = {}
_tagger_mtimes: dict[str, float] = {}
_wsd_cache: dict[str, Any] = {}
_mapper_cache: dict[str, Any] = {}
_wn_runtime_cache: dict[str, Any] = {}
_constraint_cache: dict[str, Any] | None = None
_constraint_mtime: float | None = None
_basic_lemma_cache: dict[str, str] | None = None
_basic_lemma_mtime: float | None = None
_jmdict_cache: Any | None = None
_jmdict_usas_cache: dict[str, str] | None = None
_layer1_source_cache: dict[str, dict[str, Any]] = {}
_mrw_encoder: Any | None = None
_wn_lexicons_ready: bool = False
_semantic_pipeline_cache: dict[str, Any] = {}
_llm_router: Any | None = None
_llm_router_lock = threading.Lock()
from src.statistics.domain_stats import compute_domain_frequency
from src.statistics.frequency import compute_lemma_frequency
from src.statistics.summary import compute_summary
from src.utils.file_io import read_json_file
from src.utils.file_io import read_text_file, write_csv, write_csv_bundle, write_json


def default_lexicon_path() -> str:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    return str(data_dir / "lexicon.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Japanese semantic domain analysis tool."
    )
    parser.add_argument("--input", type=str, help="Path to input text file.")
    parser.add_argument("--text", type=str, help="Raw Japanese text input.")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the desktop GUI.",
    )
    parser.add_argument(
        "--gui-mode",
        type=str,
        default="webview",
        choices=["webview"],
        help="Choose the GUI backend.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for JSON or CSV. Ignored when --bundle-dir is used.",
    )
    parser.add_argument(
        "--bundle-dir",
        type=str,
        help="Output directory for separate CSV exports: tokens, lemma_frequency, domain_frequency, summary.",
    )
    parser.add_argument(
        "--lexicon",
        type=str,
        default=default_lexicon_path(),
        help="Path to semantic lexicon JSON file.",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "usas_categories.json"),
        help="Path to USAS categories JSON file.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        choices=["zh", "ja", "en"],
        help="Language for domain labels.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="C",
        choices=["A", "B", "C"],
        help="Sudachi split mode.",
    )
    parser.add_argument(
        "--unknown-domain",
        type=str,
        default="Z99",
        help="Fallback domain code when no semantic domain is matched.",
    )
    parser.add_argument(
        "--min-frequency",
        type=int,
        default=1,
        help="Minimum frequency threshold for lemma/domain stats.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Limit frequency tables to the top N items.",
    )
    parser.add_argument(
        "--no-bert-wsd",
        action="store_true",
        help="Disable local BERT-based WSD and keep baseline first-candidate mapping.",
    )
    parser.add_argument(
        "--bert-model-dir",
        type=str,
        default=None,
        help="Local BERT model directory. Default: model/bert-base-japanese-v3 (then model/, models/bert-jp).",
    )
    return parser.parse_args()


def _get_cached_tokenizer(tokenizer: str, mode: str) -> BaseTokenizer:
    key = ((tokenizer or "sudachi").strip().lower(), (mode or "C").strip().upper())
    with _cache_lock:
        if key not in _tokenizer_cache:
            _tokenizer_cache[key] = create_tokenizer(tokenizer=key[0], mode=key[1])
        return _tokenizer_cache[key]


def _get_cached_tagger(
    lexicon_path: str,
    categories_path: str,
    unknown_domain: str,
    language: str,
) -> SemanticTagger:
    key = (lexicon_path, categories_path, unknown_domain, language)
    current_mtime = _lexicon_mtime(lexicon_path)
    with _cache_lock:
        cached = _tagger_cache.get(key)
        if cached is not None and current_mtime is not None:
            cached_mtime = _tagger_mtimes.get(lexicon_path)
            if cached_mtime is not None and cached_mtime >= current_mtime:
                return cached
            del _tagger_cache[key]
            _tagger_mtimes.pop(lexicon_path, None)
        elif cached is not None and current_mtime is None:
            return cached
        tagger = SemanticTagger(
            lexicon_path=lexicon_path,
            categories_path=categories_path,
            unknown_domain=unknown_domain,
            language=language,
        )
        _tagger_cache[key] = tagger
        if current_mtime is not None:
            _tagger_mtimes[lexicon_path] = current_mtime
        return tagger


def _lexicon_mtime(path: str) -> float | None:
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def clear_tagger_cache() -> None:
    """Discard all cached SemanticTagger instances (call after lexicon edits)."""
    with _cache_lock:
        for item in _mapper_cache.values():
            if isinstance(item, dict) and "conn" in item:
                try:
                    item["conn"].close()
                except Exception:
                    pass
        _tagger_cache.clear()
        _tagger_mtimes.clear()
        _tokenizer_cache.clear()
        _wsd_cache.clear()
        _mapper_cache.clear()
        _wn_runtime_cache.clear()
    global _constraint_cache, _constraint_mtime, _basic_lemma_cache, _basic_lemma_mtime
    _constraint_cache = None
    _constraint_mtime = None
    _basic_lemma_cache = None
    _basic_lemma_mtime = None
    global _jmdict_cache, _jmdict_usas_cache
    _jmdict_cache = None
    _jmdict_usas_cache = None
    _layer1_source_cache.clear()
    global _mrw_encoder, _llm_router
    _mrw_encoder = None
    _semantic_pipeline_cache.clear()
    if _llm_router is not None:
        try:
            _llm_router.close()
        except Exception:
            pass
        _llm_router = None


def _basic_lemma_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "mapping" / "basic_lemma_domain.json"


def _load_basic_lemma_mapping() -> dict[str, str]:
    global _basic_lemma_cache, _basic_lemma_mtime
    path = _basic_lemma_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _basic_lemma_cache = {}
        _basic_lemma_mtime = None
        return {}
    if _basic_lemma_cache is not None and _basic_lemma_mtime is not None and _basic_lemma_mtime >= mtime:
        return _basic_lemma_cache
    raw = read_json_file(str(path))
    if not isinstance(raw, dict):
        _basic_lemma_cache = {}
        _basic_lemma_mtime = mtime
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or k.startswith("_"):
            continue
        key = k.strip()
        val = str(v).strip()
        if key and val:
            out[key] = val
    _basic_lemma_cache = out
    _basic_lemma_mtime = mtime
    return out


def _constraint_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "mapping" / "semantic_constraints.json"


def _load_constraints() -> dict[str, Any]:
    global _constraint_cache, _constraint_mtime
    path = _constraint_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _constraint_cache = {}
        _constraint_mtime = None
        return {}
    if _constraint_cache is not None and _constraint_mtime is not None and _constraint_mtime >= mtime:
        return _constraint_cache
    raw = read_json_file(str(path))
    if not isinstance(raw, dict):
        _constraint_cache = {}
        _constraint_mtime = mtime
        return {}
    # Environment overrides (useful for smoke scripts / experiments without editing files).
    # - BUNSEKI_ENABLE_MIPVU_LAYER3: "1"/"true" to enable Layer3 stub
    # - BUNSEKI_MRW_THRESHOLD: float override for MRW distance threshold
    enable_env = str(os.getenv("BUNSEKI_ENABLE_MIPVU_LAYER3", "") or "").strip().lower()
    if enable_env in {"1", "true", "yes", "on"}:
        raw["enable_mipvu_layer3"] = True
    thr_env = str(os.getenv("BUNSEKI_MRW_THRESHOLD", "") or "").strip()
    if thr_env:
        try:
            raw["mrw_distance_threshold"] = float(thr_env)
        except ValueError:
            pass

    _constraint_cache = raw
    _constraint_mtime = mtime
    return raw


def _normalize_domains(items: Any) -> list[str]:
    if isinstance(items, str):
        values = [items]
    elif isinstance(items, list):
        values = [str(x) for x in items]
    else:
        return []
    out: list[str] = []
    for v in values:
        code = str(v).strip()
        if code and code not in out:
            out.append(code)
    return out


def _pos_head(pos: str) -> str:
    value = str(pos or "").strip()
    if not value:
        return ""
    # Sudachi/MeCab: comma; some dictionaries: hyphen-like separators.
    return value.split(",")[0].split("-")[0].split("－")[0].strip()


def _apply_semantic_constraints(tagged_tokens: list[dict[str, Any]]) -> dict[str, int]:
    cfg = _load_constraints()
    # Hard rule: function words/punctuation should not carry semantic domains.
    force_trash_pos = {"助詞", "助動詞", "補助記号", "記号", "空白"}
    stopwords = {str(x).strip() for x in cfg.get("stopwords", []) if str(x).strip()}
    allow_pos = {str(x).strip() for x in cfg.get("allowed_pos_prefixes", []) if str(x).strip()}
    block_pos = {str(x).strip() for x in cfg.get("blocked_pos_prefixes", []) if str(x).strip()}
    max_candidates = int(cfg.get("max_candidates", 3) or 3)
    token_overrides = cfg.get("token_overrides", {}) if isinstance(cfg.get("token_overrides", {}), dict) else {}
    token_blacklist = cfg.get("token_domain_blacklist", {}) if isinstance(cfg.get("token_domain_blacklist", {}), dict) else {}
    pos_blacklist = cfg.get("pos_domain_blacklist", {}) if isinstance(cfg.get("pos_domain_blacklist", {}), dict) else {}
    wl = {str(x).strip() for x in cfg.get("domain_whitelist", []) if str(x).strip()}
    basic_lemma_map = _load_basic_lemma_mapping()

    stats = {
        "filtered_tokens": 0,
        "override_tokens": 0,
        "basic_lemma_hits": 0,
        "capped_candidates": 0,
        "basic_assigned_tokens": 0,
    }
    for tok in tagged_tokens:
        surface = str(tok.get("surface", "") or "").strip()
        lemma = str(tok.get("lemma", "") or "").strip()
        lemma_norm = _normalize_lemma_key(lemma)
        surface_norm = _normalize_lemma_key(surface)
        pos = str(tok.get("pos", "") or "").strip()
        pos_head = _pos_head(pos)
        is_symbol_only = bool(surface) and all(
            (not ch.isalnum()) and (not ("\u3040" <= ch <= "\u30ff")) and (not ("\u4e00" <= ch <= "\u9fff"))
            for ch in surface
        )
        old_codes = _normalize_domains(tok.get("domain_codes", []))
        old_labels = [str(x).strip() for x in list(tok.get("domain_labels", [])) if str(x).strip()]
        label_map = dict(zip(old_codes, old_labels))
        candidates = list(old_codes)
        if not candidates:
            candidates = ["Z99"]
        basic_source = "wordnet"
        basic_code = candidates[0]

        if (
            pos_head in force_trash_pos
            or is_symbol_only
            or pos_head in block_pos
            or (allow_pos and pos_head and pos_head not in allow_pos)
        ):
            tok["basic_candidates"] = ["Z99"]
            tok["basic_domain_code"] = "Z99"
            if pos_head in force_trash_pos:
                tok["basic_domain_source"] = "function_word_filtered"
            elif is_symbol_only:
                tok["basic_domain_source"] = "symbol_filtered"
            else:
                tok["basic_domain_source"] = "pos_filtered"
            tok["domain_codes"] = ["Z99"]
            tok["domain_code"] = "Z99"
            tok["domain"] = "Z99"
            stats["filtered_tokens"] += 1
            stats["basic_assigned_tokens"] += 1
            continue
        if surface in stopwords or lemma in stopwords:
            tok["basic_candidates"] = ["Z99"]
            tok["basic_domain_code"] = "Z99"
            tok["basic_domain_source"] = "stopword"
            tok["domain_codes"] = ["Z99"]
            tok["domain_code"] = "Z99"
            tok["domain"] = "Z99"
            stats["filtered_tokens"] += 1
            stats["basic_assigned_tokens"] += 1
            continue

        override = _normalize_domains(
            token_overrides.get(lemma) or token_overrides.get(surface) or token_overrides.get(lemma_norm)
        )
        basic_override = (
            basic_lemma_map.get(lemma) or basic_lemma_map.get(surface) or basic_lemma_map.get(lemma_norm) or basic_lemma_map.get(surface_norm)
        )
        if basic_override:
            override = [basic_override]
            basic_source = "basic_lemma"
            basic_code = basic_override
            stats["basic_lemma_hits"] += 1
        if override:
            candidates = override
            if basic_source != "basic_lemma":
                basic_source = "token_override"
                basic_code = candidates[0]
            stats["override_tokens"] += 1

        blocked = set(
            _normalize_domains(token_blacklist.get(lemma) or token_blacklist.get(surface))
            + _normalize_domains(pos_blacklist.get(pos_head))
        )
        if blocked:
            candidates = [c for c in candidates if c not in blocked]

        if wl:
            candidates = [c for c in candidates if c in wl]

        if len(candidates) > max_candidates:
            candidates = candidates[:max_candidates]
            stats["capped_candidates"] += 1
        if not candidates:
            candidates = ["Z99"]
            if basic_code != "Z99":
                basic_source = f"{basic_source}_fallback_z99"
            basic_code = "Z99"

        tok["basic_candidates"] = list(candidates)
        tok["basic_domain_code"] = basic_code if basic_code else candidates[0]
        tok["basic_domain_source"] = basic_source
        stats["basic_assigned_tokens"] += 1
        tok["domain_codes"] = candidates
        tok["domain_code"] = candidates[0]
        tok["domain"] = candidates[0]
        mapped_labels = [label_map[c] for c in candidates if c in label_map]
        if mapped_labels:
            tok["domain_labels"] = mapped_labels
            tok["domain_label"] = " / ".join(mapped_labels)
    return stats


def _resolve_bert_model_dir(model_dir: Optional[str]) -> Optional[str]:
    def _is_valid_model_dir(path: Path) -> bool:
        if not path.exists() or not path.is_dir():
            return False
        has_config = (path / "config.json").exists()
        has_weights = (path / "pytorch_model.bin").exists() or (path / "model.safetensors").exists()
        has_tokenizer = (path / "tokenizer_config.json").exists() or (path / "vocab.txt").exists()
        return has_config and has_weights and has_tokenizer

    if model_dir:
        p = Path(model_dir)
        if _is_valid_model_dir(p):
            return str(p)
        return None
    for candidate in ("model/bert-base-japanese-v3", "model", "models/bert-jp"):
        p = Path(candidate)
        if _is_valid_model_dir(p):
            return str(p)
    return None


def _build_domain_descriptions(categories_path: str) -> dict[str, str]:
    raw = read_json_file(categories_path)
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for code, value in raw.items():
        domain = str(code).strip()
        if not domain:
            continue
        if isinstance(value, dict):
            desc = (
                str(value.get("en", "")).strip()
                or str(value.get("ja", "")).strip()
                or str(value.get("zh", "")).strip()
            )
        else:
            desc = str(value).strip()
        if desc:
            out[domain] = desc
    return out


def _usas_tagset(categories_path: str) -> list[str]:
    raw = read_json_file(categories_path)
    if not isinstance(raw, dict):
        return []
    out: list[str] = []
    for code in raw:
        c = str(code).strip()
        if c and c not in out:
            out.append(c)
    return out


def _normalize_lemma_key(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).strip().lower()


def _get_cached_jmdict(repo_root: Path):
    global _jmdict_cache
    if _jmdict_cache is not None:
        return _jmdict_cache
    from src.dict.jmdict import JMdict

    _jmdict_cache = JMdict(repo_root)
    return _jmdict_cache


def _get_cached_jmdict_usas(repo_root: Path) -> dict[str, str]:
    global _jmdict_usas_cache
    if _jmdict_usas_cache is not None:
        return _jmdict_usas_cache
    path = repo_root / "jmdict_builder" / "output" / "jmdict_usas.json"
    if not path.exists():
        _jmdict_usas_cache = {}
        return _jmdict_usas_cache
    try:
        raw = read_json_file(str(path))
    except Exception:
        _jmdict_usas_cache = {}
        return _jmdict_usas_cache
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            key = _normalize_lemma_key(k)
            val = str(v or "").strip()
            if key and val:
                out[key] = val
    _jmdict_usas_cache = out
    return out


def _layer1_basic_sense_and_source_domain(
    *,
    repo_root: Path,
    lemma: str,
    categories_path: str,
) -> dict[str, Any]:
    key = _normalize_lemma_key(lemma)
    if not key:
        return {"basic_meaning": "", "source_domain_label": "Z99", "layer1_source": "missing_lemma"}
    cached = _layer1_source_cache.get(key)
    if cached is not None:
        return cached

    jmdict = _get_cached_jmdict(repo_root)
    gloss = jmdict.lookup_first_gloss(key) or ""
    static_map = _get_cached_jmdict_usas(repo_root)
    static_label = str(static_map.get(key, "") or "").strip()
    if static_label:
        out = {
            "basic_meaning": gloss,
            "source_domain_label": static_label,
            "layer1_source": "jmdict_usas_static",
            "layer1_confidence": 0.9,
            "layer1_rationale": "static_lookup",
        }
        _layer1_source_cache[key] = out
        return out

    # LLM stub: always pick from the USAS tagset.
    from src.llm.selector import USASSelectorStub

    selector = USASSelectorStub(repo_root)
    tagset = _usas_tagset(categories_path)
    choice = selector.classify_to_usas(gloss, tagset)
    out = {
        "basic_meaning": gloss,
        "source_domain_label": choice.label,
        "layer1_source": "jmdict+llm_stub" if gloss else "jmdict_missing",
        "layer1_confidence": choice.confidence,
        "layer1_rationale": choice.rationale,
    }
    _layer1_source_cache[key] = out
    return out


def _get_cached_mrw_encoder():
    global _mrw_encoder
    if _mrw_encoder is not None:
        return _mrw_encoder
    from src.metaphor.mrw import MRWEncoder

    repo_root = Path(__file__).resolve().parents[1]
    # Prefer local model directory to avoid any network access.
    # Users can place HF-compatible snapshots under:
    # - model/bert-base-japanese-v3/
    # - model/  (direct files)
    # - models/bert-jp/ (placeholder directory)
    candidates = [
        repo_root / "model" / "bert-base-japanese-v3",
        repo_root / "model",
        repo_root / "models" / "bert-jp",
    ]
    resolved: str | None = None
    for p in candidates:
        if not p.exists():
            continue
        if (p / "model.safetensors").exists() or (p / "pytorch_model.bin").exists():
            resolved = str(p)
            break
    if resolved is not None:
        _mrw_encoder = MRWEncoder(resolved, local_files_only=True)
        return _mrw_encoder

    # Fallback to remote model name (may download if local cache isn't present).
    _mrw_encoder = MRWEncoder("tohoku-nlp/bert-base-japanese-v3", local_files_only=False)
    return _mrw_encoder


def _get_cached_disambiguator(model_dir: str, categories_path: str):
    cache_key = f"{model_dir}::{categories_path}"
    cached = _wsd_cache.get(cache_key)
    if cached is not None:
        return cached

    _REPO_ROOT = Path(__file__).resolve().parents[1]
    _disamb_dir = str(_REPO_ROOT)
    if _disamb_dir not in sys.path:
        sys.path.insert(0, _disamb_dir)
    from disambiguator import Disambiguator
    from model import BertEncoder

    descriptions = _build_domain_descriptions(categories_path)
    labeled_lexicon = _load_wordnet_labeled_lexicon()
    dis = Disambiguator(
        BertEncoder(model_dir=model_dir),
        domain_descriptions=descriptions,
        labeled_lexicon=labeled_lexicon,
    )
    with _cache_lock:
        _wsd_cache[cache_key] = dis
    return dis


def _get_cached_semantic_pipeline(model_dir: str, categories_path: str):
    cache_key = f"{model_dir}::{categories_path}"
    cached = _semantic_pipeline_cache.get(cache_key)
    if cached is not None:
        return cached
    from src.pipeline.semantic_pipeline import SemanticPipeline

    descriptions = _build_domain_descriptions(categories_path)
    labeled_lexicon = _load_wordnet_labeled_lexicon()
    pipe = SemanticPipeline(
        model_dir=model_dir,
        domain_descriptions=descriptions,
        labeled_lexicon=labeled_lexicon,
        top_k=3,
    )
    with _cache_lock:
        _semantic_pipeline_cache[cache_key] = pipe
    return pipe


def _wordnet_db_path() -> str | None:
    env_path = str(os.environ.get("BUNSEKI_WN_DB_PATH", "")).strip()
    if env_path and Path(env_path).exists():
        return env_path
    candidate = Path(__file__).resolve().parents[1] / "data" / "wordnet" / "wnjpn.db"
    if candidate.exists():
        return str(candidate)
    return None


def _wn_usas_map_path() -> str | None:
    env_path = str(os.environ.get("BUNSEKI_WN_USAS_MAP_PATH", "")).strip()
    if env_path and Path(env_path).exists():
        return env_path
    candidate = Path(__file__).resolve().parents[1] / "data" / "mapping" / "wn_pwn_usas_map.json"
    if candidate.exists():
        return str(candidate)
    return None


def _load_wordnet_labeled_lexicon() -> dict[str, list[str]]:
    path = Path(__file__).resolve().parents[1] / "data" / "mapping" / "wordnet_usas_map.json"
    if not path.exists():
        return {}
    raw = read_json_file(str(path))
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for lemma, labels in raw.items():
        if not isinstance(lemma, str) or lemma.startswith("_"):
            continue
        key = lemma.strip()
        if not key:
            continue
        if isinstance(labels, str):
            out[key] = [labels.strip()] if labels.strip() else []
        elif isinstance(labels, list):
            out[key] = [str(x).strip() for x in labels if str(x).strip()]
    return out


def _wn_pos_from_jp(pos_head: str) -> str:
    pos = str(pos_head or "").strip()
    if pos in {"名詞", "代名詞"}:
        return "n"
    if pos in {"動詞"}:
        return "v"
    if pos in {"形容詞", "連体詞"}:
        return "a"
    if pos in {"副詞"}:
        return "r"
    return ""


def _get_cached_wordnet_runtime():
    db_path = _wordnet_db_path()
    map_path = _wn_usas_map_path()
    if not db_path or not map_path:
        return None
    cache_key = f"{db_path}::{map_path}"
    cached = _mapper_cache.get(cache_key)
    if cached is not None:
        return cached
    conn = sqlite3.connect(db_path)
    pwn_to_usas = read_json_file(map_path)
    if not isinstance(pwn_to_usas, dict):
        pwn_to_usas = {}
    mapper = {
        "conn": conn,
        "pwn_to_usas": pwn_to_usas,
    }
    with _cache_lock:
        _mapper_cache[cache_key] = mapper
    return mapper


def _get_cached_wn_wordnet():
    cached = _wn_runtime_cache.get("omw-ja:2.0")
    if cached is not None:
        return cached
    global _wn_lexicons_ready
    try:
        import wn  # type: ignore
    except Exception:
        return None
    try:
        if not _wn_lexicons_ready:
            # Preload omw-en dependency once to suppress runtime dependency warnings.
            try:
                wn.Wordnet("omw-en:2.0")
            except Exception:
                try:
                    wn.download("omw-en:2.0")
                except Exception:
                    pass
            _wn_lexicons_ready = True
        w = wn.Wordnet("omw-ja:2.0")
    except Exception:
        try:
            wn.download("omw-ja:2.0")
            w = wn.Wordnet("omw-ja:2.0")
        except Exception:
            return None
    with _cache_lock:
        _wn_runtime_cache["omw-ja:2.0"] = w
    return w


def _wordnet_backfill_candidates(token: str, mapper: Any) -> list[str]:
    token_norm = str(token or "").strip()
    if not token_norm:
        return []
    w = _get_cached_wn_wordnet()
    if w is None:
        return []
    try:
        synsets = w.synsets(token_norm)
    except Exception:
        return []
    lexicon = _load_wordnet_labeled_lexicon()
    if not isinstance(lexicon, dict) or not lexicon:
        return []
    votes: dict[str, float] = {}
    for syn in synsets:
        try:
            words = syn.words()
        except Exception:
            continue
        seen_lemmas: set[str] = set()
        for word in words:
            forms: list[str] = []
            try:
                forms.extend([str(x).strip() for x in word.forms() if str(x).strip()])
            except Exception:
                pass
            try:
                lemma = str(word.lemma()).strip()
                if lemma:
                    forms.append(lemma)
            except Exception:
                pass
            for form in forms:
                if form in seen_lemmas:
                    continue
                seen_lemmas.add(form)
                domains = lexicon.get(form, [])
                for dom in domains:
                    code = str(dom).strip()
                    if not code:
                        continue
                    votes[code] = votes.get(code, 0.0) + 1.0
    ranked = sorted(votes.items(), key=lambda item: item[1], reverse=True)
    return [code for code, _ in ranked]


def _apply_layer1_dictionary(tagged_tokens: list[dict[str, Any]]) -> dict[str, int]:
    mapper = _get_cached_wordnet_runtime()
    stats = {"dictionary_hits": 0, "dictionary_misses": 0, "ambiguous_candidates": 0, "wordnet_backfill_hits": 0}
    if mapper is None:
        stats["dictionary_misses"] = len(tagged_tokens)
        return stats
    conn = mapper["conn"]
    pwn_to_usas = mapper["pwn_to_usas"]
    for tok in tagged_tokens:
        lemma = str(tok.get("lemma", "") or "").strip()
        pos = str(tok.get("pos", "") or "").strip()
        pos_head = _pos_head(pos)
        wn_pos = _wn_pos_from_jp(pos_head)
        candidates: list[str] = []
        if lemma and wn_pos:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT s.synset
                    FROM sense se
                    JOIN synset s ON se.synset = s.synset
                    WHERE se.lemma = ? AND s.pos = ?
                    """,
                    (lemma, wn_pos),
                )
                rows = cur.fetchall()
            except Exception:
                rows = []
            votes: dict[str, float] = {}
            for (synset_id,) in rows:
                labels = pwn_to_usas.get(str(synset_id), [])
                if isinstance(labels, str):
                    labels = [labels]
                if not isinstance(labels, list):
                    continue
                for label in labels:
                    code = str(label).strip()
                    if not code:
                        continue
                    votes[code] = votes.get(code, 0.0) + 1.0
            candidates = [code for code, _ in sorted(votes.items(), key=lambda item: item[1], reverse=True)]
        if not candidates:
            candidates = _wordnet_backfill_candidates(lemma or str(tok.get("surface", "") or ""), mapper)
            if candidates:
                stats["wordnet_backfill_hits"] += 1
        if candidates:
            tok["domain_codes"] = list(candidates)
            tok["domain_code"] = candidates[0]
            tok["domain"] = candidates[0]
            stats["dictionary_hits"] += 1
            if len(candidates) > 1:
                stats["ambiguous_candidates"] += 1
        else:
            stats["dictionary_misses"] += 1
    return stats


def _apply_bert_wsd(
    text: str,
    tagged_tokens: list[dict[str, Any]],
    *,
    use_bert_wsd: bool,
    bert_model_dir: Optional[str],
    categories_path: str,
    layer_stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    cfg = _load_constraints()
    similarity_threshold = float(cfg.get("wsd_similarity_threshold", 0.2) or 0.2)
    location_like_tokens = {str(x).strip() for x in cfg.get("location_like_tokens", []) if str(x).strip()}
    location_forbidden = set(_normalize_domains(cfg.get("location_forbidden_domains", [])))
    meta: dict[str, Any] = {
        "enabled": False,
        "applied_tokens": 0,
        "model_dir": None,
        "fallback_reason": "",
        "low_confidence_to_z99": 0,
    }
    if not use_bert_wsd:
        meta["fallback_reason"] = "disabled"
        return meta
    resolved = _resolve_bert_model_dir(bert_model_dir)
    if not resolved:
        meta["fallback_reason"] = "model_not_found"
        return meta
    try:
        disambiguator = _get_cached_disambiguator(resolved, categories_path)
    except Exception as exc:  # noqa: BLE001
        meta["fallback_reason"] = f"bert_load_failed: {exc}"
        return meta

    context_tokens = [str(tok.get("surface", "") or "") for tok in tagged_tokens]
    for idx, tok in enumerate(tagged_tokens):
        candidates = [str(x).strip() for x in list(tok.get("domain_codes", [])) if str(x).strip()]
        lemma = str(tok.get("lemma", "") or "").strip()
        surface = str(tok.get("surface", "") or "").strip()
        basic_source = str(tok.get("basic_domain_source", "") or "").strip()
        if basic_source in {"function_word_filtered", "symbol_filtered", "pos_filtered", "stopword"}:
            tok["domain_codes"] = ["Z99"]
            tok["domain_code"] = "Z99"
            tok["domain"] = "Z99"
            continue
        if not candidates or candidates == ["Z99"]:
            vector_candidates = disambiguator.nearest_neighbor_candidates(surface or lemma)
            if vector_candidates:
                candidates = vector_candidates
                tok["domain_codes"] = list(candidates)
                tok["domain_code"] = candidates[0]
                tok["domain"] = candidates[0]
                if layer_stats is not None:
                    layer_stats["layer2_vector_hits"] = int(layer_stats.get("layer2_vector_hits", 0)) + 1
        if (lemma in location_like_tokens or surface in location_like_tokens) and location_forbidden:
            candidates = [c for c in candidates if c not in location_forbidden]
            if not candidates:
                candidates = ["Z99"]
                tok["domain_codes"] = candidates
                tok["domain_code"] = "Z99"
                tok["domain"] = "Z99"
                continue
        if len(candidates) <= 1:
            continue
        left = max(0, idx - 3)
        right = min(len(context_tokens), idx + 4)
        context = "".join(context_tokens[left:right]) or text
        chosen, _score = disambiguator.disambiguate(
            context=context,
            token=surface or lemma,
            candidates=candidates,
            similarity_threshold=similarity_threshold,
        )
        if chosen == "Z99":
            meta["low_confidence_to_z99"] = int(meta["low_confidence_to_z99"]) + 1
        tok["domain_code"] = chosen
        tok["domain"] = chosen
        labels = list(tok.get("domain_labels", []))
        if labels:
            code_to_label = dict(zip(candidates, labels))
            label = code_to_label.get(chosen, labels[0])
            tok["domain_label"] = label
            tok["domain_labels"] = [label]
        tok["domain_codes"] = [chosen]
        meta["applied_tokens"] = int(meta["applied_tokens"]) + 1
        if layer_stats is not None:
            layer_stats["layer3_adjudications"] = int(layer_stats.get("layer3_adjudications", 0)) + 1

    meta["enabled"] = True
    meta["model_dir"] = resolved
    return meta


def _compute_mrw_distance(
    token_text: str,
    basic_meaning: str,
    context_text: str,
) -> float:
    """Compute MRW cosine distance between basic meaning and context embeddings.

    Returns a float in [0, 2] where higher values indicate more metaphorical usage.
    Returns 0.0 if the MRW encoder is unavailable or basic_meaning is empty.
    """
    if not basic_meaning or not token_text or not context_text:
        return 0.0
    try:
        encoder = _get_cached_mrw_encoder()
        result = encoder.mrw_distance(
            basic_sentence=basic_meaning,
            context_sentence=context_text,
            word=token_text,
        )
        return result.distance
    except Exception:
        return 0.0


def _mrw_threshold_for_pos(pos: str) -> float:
    """Get the MRW distance threshold for a given POS tag."""
    from config.settings import MRW_THRESHOLDS

    pos = str(pos or "").strip()
    # Try exact match first, then prefix match, then default
    if pos in MRW_THRESHOLDS:
        return float(MRW_THRESHOLDS[pos])
    # Check if any key is a prefix of pos (e.g., "名詞" matches "名詞,普通名詞,...")
    for key, val in MRW_THRESHOLDS.items():
        if key != "default" and pos.startswith(key):
            return float(val)
    return float(MRW_THRESHOLDS.get("default", 0.35))


def _get_cached_llm_router():
    """Return a cached LLMRouter instance, or None if LLM is unavailable.

    Reloads config on each call so that Settings UI changes take effect
    without restarting the backend.
    """
    global _llm_router
    from config.settings import reload_config

    reload_config()
    if not is_llm_available():
        if _llm_router is not None:
            try:
                _llm_router.close()
            except Exception:
                pass
            _llm_router = None
        return None
    with _llm_router_lock:
        if _llm_router is not None:
            return _llm_router
        try:
            from llm.router import LLMRouter

            _llm_router = LLMRouter()
            return _llm_router
        except Exception:
            return None


def _build_source_candidates(
    current_tag: str, usas_labels: dict[str, str]
) -> list[tuple[str, str]]:
    """Build candidate list for source domain classification.

    Always includes the current tag and Z99, plus semantically adjacent
    tags (same top-level prefix category).
    """
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(tag: str) -> None:
        tag = tag.strip()
        if not tag or tag in seen:
            return
        seen.add(tag)
        label = usas_labels.get(tag, tag)
        candidates.append((tag, label))

    _add(current_tag)

    prefix = current_tag[0] if current_tag else ""
    if prefix and prefix != "Z":
        for tag in sorted(usas_labels):
            if tag.startswith(prefix) and tag != current_tag:
                _add(tag)
                if len(candidates) >= 6:
                    break

    _add("Z99")
    return candidates


def build_result(
    text: str,
    lexicon_path: str,
    categories_path: str,
    language: str = "en",
    tokenizer: str = "sudachi",
    mode: str = "C",
    unknown_domain: str = "Z99",
    min_frequency: int = 1,
    top_n: int | None = None,
    use_bert_wsd: bool = True,
    bert_model_dir: Optional[str] = None,
) -> Dict[str, Any]:
    tokenizer_impl = _get_cached_tokenizer(tokenizer, mode)
    tagger = _get_cached_tagger(
        lexicon_path=lexicon_path,
        categories_path=categories_path,
        unknown_domain=unknown_domain,
        language=language,
    )

    token_tuples = tokenizer_impl.tokenize(text)
    tagged_tokens = tagger.tag_tokens(token_tuples)
    repo_root = Path(__file__).resolve().parents[1]
    layer_stats: dict[str, int] = {
        "layer1_dictionary_hits": 0,
        "layer1_dictionary_misses": 0,
        "layer1_wordnet_backfill_hits": 0,
        "layer2_vector_hits": 0,
        "layer2_mrw_fallback_used": 0,
        "layer3_adjudications": 0,
        "layer2_mrw_candidates": 0,
        "layer3_mipvu_tokens": 0,
        "layer3_final_resolved": 0,
    }
    layer1 = _apply_layer1_dictionary(tagged_tokens)
    layer_stats["layer1_dictionary_hits"] = int(layer1.get("dictionary_hits", 0))
    layer_stats["layer1_dictionary_misses"] = int(layer1.get("dictionary_misses", 0))
    layer_stats["layer1_wordnet_backfill_hits"] = int(layer1.get("wordnet_backfill_hits", 0))
    constraint_stats = _apply_semantic_constraints(tagged_tokens)
    # Layer1 (MIPVU): attach basic sense and source-domain label for content words only.
    for tok in tagged_tokens:
        basic_source = str(tok.get("basic_domain_source", "") or "").strip()
        if basic_source in {"function_word_filtered", "symbol_filtered", "pos_filtered", "stopword"}:
            continue
        lemma = str(tok.get("lemma", "") or "").strip()
        if not lemma:
            continue
        layer1_info = _layer1_basic_sense_and_source_domain(
            repo_root=repo_root,
            lemma=lemma,
            categories_path=categories_path,
        )
        tok["basic_meaning"] = layer1_info.get("basic_meaning", "")
        tok["source_domain_label"] = layer1_info.get("source_domain_label", "Z99")
        tok["layer1_source"] = layer1_info.get("layer1_source", "")
        tok["layer1_confidence"] = layer1_info.get("layer1_confidence", 0.0)
        tok["layer1_rationale"] = layer1_info.get("layer1_rationale", "")

    # New robust 3-layer semantic pipeline:
    # L1 -> L2(vector top-k) -> L2(MRW fallback top-k) -> L3(adjudication)
    # If LLM is available, L3 also includes MIPVU metaphor confirmation + target domain.
    cfg = _load_constraints()
    resolved_model = _resolve_bert_model_dir(bert_model_dir)
    semantic_pipeline = None
    if resolved_model:
        try:
            semantic_pipeline = _get_cached_semantic_pipeline(resolved_model, categories_path)
        except Exception:
            semantic_pipeline = None
    domain_pool = [d for d in _usas_tagset(categories_path) if d and d != "Z99"]
    usas_labels = load_usas_labels_ja(categories_path)
    llm_router = _get_cached_llm_router()
    mipvu_enabled = bool(is_llm_available() and llm_router is not None and semantic_pipeline is not None)
    for tok in tagged_tokens:
        basic_source = str(tok.get("basic_domain_source", "") or "").strip()
        if basic_source in {"function_word_filtered", "symbol_filtered", "pos_filtered", "stopword"}:
            tok["mrw_distance"] = 0.0
            tok["is_metaphor_candidate"] = False
            tok["pipeline_source"] = "filtered"
            continue
        token_text = str(tok.get("surface", "") or tok.get("lemma", "") or "").strip()
        if not token_text:
            continue
        prior_candidates = [str(x).strip() for x in list(tok.get("basic_candidates", [])) if str(x).strip()]
        # L1 can miss; keep previous candidate if available.
        if not prior_candidates:
            dc = str(tok.get("domain_code", "") or "").strip()
            if dc:
                prior_candidates = [dc]
        if semantic_pipeline is None:
            # Deterministic degraded path: keep L1 and mark unresolved by higher layers.
            fallback = prior_candidates[0] if prior_candidates else "Z99"
            tok["domain_code"] = fallback
            tok["domain_codes"] = [fallback]
            tok["domain"] = fallback
            tok["pipeline_source"] = "l1_only"
            tok["is_metaphor_candidate"] = False
            tok["mrw_distance"] = 0.0
            continue
        decision = semantic_pipeline.adjudicate(
            token=token_text,
            context=text,
            prior_candidates=prior_candidates,
            domain_pool=domain_pool,
        )
        tok["vector_candidates"] = decision.vector_candidates
        tok["mrw_candidates"] = decision.mrw_candidates[:3]
        tok["scores_by_domain"] = decision.scores_by_domain
        tok["domain_code"] = decision.final_domain
        tok["domain_codes"] = [decision.final_domain]
        tok["domain"] = decision.final_domain
        tok["pipeline_source"] = (
            "l2_vector" if decision.used_vector else ("l2_mrw_fallback" if decision.used_mrw_fallback else "l1_only")
        )
        # Compute real MRW distance from BERT cosine similarity when LLM is
        # available; otherwise use the boolean flag from the fallback path.
        if mipvu_enabled:
            basic_meaning = str(tok.get("basic_meaning", "") or "").strip()
            real_distance = _compute_mrw_distance(
                token_text=token_text,
                basic_meaning=basic_meaning,
                context_text=text,
            )
            tok["mrw_distance"] = real_distance
            pos = str(tok.get("pos", "") or "").strip()
            threshold = _mrw_threshold_for_pos(pos)
            tok["is_metaphor_candidate"] = real_distance >= threshold
        else:
            tok["is_metaphor_candidate"] = bool(decision.used_mrw_fallback)
            tok["mrw_distance"] = float(0.0 if not decision.used_mrw_fallback else 1.0)
        layer_stats["layer2_vector_hits"] = int(layer_stats.get("layer2_vector_hits", 0)) + (1 if decision.used_vector else 0)
        layer_stats["layer2_mrw_fallback_used"] = int(layer_stats.get("layer2_mrw_fallback_used", 0)) + (
            1 if decision.used_mrw_fallback else 0
        )
        layer_stats["layer3_adjudications"] = int(layer_stats.get("layer3_adjudications", 0)) + 1
        layer_stats["layer3_final_resolved"] = int(layer_stats.get("layer3_final_resolved", 0)) + (
            1 if decision.final_domain != "Z99" else 0
        )
    layer_stats["layer2_mrw_candidates"] = int(
        sum(len(list(t.get("mrw_candidates", []))) for t in tagged_tokens if isinstance(t.get("mrw_candidates"), list))
    )
    # --- LLM-MIPVU Layer 3: metaphor confirmation + target domain identification ---
    # Only runs when: (a) LLM is available, (b) SemanticPipeline was loaded.
    # For each metaphor candidate, the LLM confirms the MRW decision, refines the
    # source domain, and identifies the target domain (the abstract concept the
    # word metaphorically refers to).  All prompts are multiple-choice — never
    # free generation — to eliminate hallucination risk.
    if mipvu_enabled and usas_labels:
        layer_stats["layer3_mipvu_tokens"] = 0
        for tok in tagged_tokens:
            is_candidate = bool(tok.get("is_metaphor_candidate", False))
            if not is_candidate:
                tok["is_metaphor"] = False
                tok["target_domain"] = None
                tok["target_domain_label"] = None
                tok["mipvu_path"] = "not_candidate"
                continue
            token_text = str(tok.get("lemma", "") or tok.get("surface", "") or "").strip()
            if not token_text:
                continue
            basic_meaning = str(tok.get("basic_meaning", "") or "").strip()
            try:
                # Step A: LLM confirms MRW
                is_confirmed = llm_router.confirm_mrw(
                    word=token_text,
                    basic_meaning=basic_meaning,
                    sentence=text,
                )
                if not is_confirmed:
                    tok["is_metaphor"] = False
                    tok["target_domain"] = None
                    tok["target_domain_label"] = None
                    tok["mipvu_path"] = "llm_rejected"
                    continue

                # Step B: LLM refines source domain
                src_label = str(tok.get("source_domain_label", "Z99") or "Z99").strip()
                if not src_label or src_label == "Z99":
                    src_label = str(tok.get("domain_code", "Z99") or "Z99").strip()
                src_candidates = _build_source_candidates(src_label, usas_labels)
                refined_source = llm_router.classify_source_domain(
                    word=token_text,
                    basic_meaning=basic_meaning,
                    candidates=src_candidates,
                )
                tok["source_domain"] = refined_source
                tok["source_domain_label"] = usas_labels.get(refined_source, refined_source)

                # Step C: LLM identifies target domain
                target_tag = llm_router.identify_target_domain(
                    word=token_text,
                    sentence=text,
                    source_tag=refined_source,
                    all_tags=usas_labels,
                )
                tok["is_metaphor"] = True
                tok["target_domain"] = target_tag
                tok["target_domain_label"] = usas_labels.get(target_tag, target_tag)
                tok["mipvu_path"] = "llm_confirm+llm_src+llm_tgt"
                tok["confidence"] = "medium"
                layer_stats["layer3_mipvu_tokens"] = int(layer_stats.get("layer3_mipvu_tokens", 0)) + 1
            except Exception:
                tok["is_metaphor"] = bool(is_candidate)
                tok["target_domain"] = None
                tok["target_domain_label"] = None
                tok["mipvu_path"] = "llm_failed_fallback"
    else:
        # No LLM available — mark all tokens with deterministic fallback.
        for tok in tagged_tokens:
            if tok.get("is_metaphor_candidate", False):
                tok["is_metaphor"] = True
                tok["target_domain"] = None
                tok["target_domain_label"] = None
                tok["mipvu_path"] = "deterministic_only"
            else:
                tok["is_metaphor"] = False
                tok["target_domain"] = None
                tok["target_domain_label"] = None
                tok["mipvu_path"] = "not_candidate"

    for tok in tagged_tokens:
        # Backward-compatible aliases for clients already reading `base_domain_*`.
        tok["base_domain_code"] = tok.get("basic_domain_code", "Z99")
        tok["base_domain_codes"] = tok.get("basic_candidates", [tok.get("base_domain_code", "Z99")])
    # Only use legacy BERT WSD as fallback when the new SemanticPipeline is unavailable.
    if semantic_pipeline is None:
        wsd_meta = _apply_bert_wsd(
            text=text,
            tagged_tokens=tagged_tokens,
            use_bert_wsd=use_bert_wsd,
            bert_model_dir=bert_model_dir,
            categories_path=categories_path,
            layer_stats=layer_stats,
        )
    else:
        wsd_meta = {
            "enabled": False,
            "applied_tokens": 0,
            "model_dir": None,
            "fallback_reason": "using_semantic_pipeline",
        }
    # Assign stable offsets once (used by KWIC / context jump). This avoids repeated
    # scanning in downstream views and keeps offsets aligned with the tokenizer output.
    cursor = 0
    for tok in tagged_tokens:
        surface = str(tok.get("surface", "") or "")
        if not surface:
            continue
        off = text.find(surface, cursor)
        if off < 0:
            continue
        tok["offset"] = off
        cursor = off + len(surface)
    lemma_frequency = compute_lemma_frequency(
        tagged_tokens, min_count=min_frequency, top_n=top_n
    )
    domain_frequency = compute_domain_frequency(
        tagged_tokens, min_count=min_frequency, top_n=top_n
    )
    summary = compute_summary(tagged_tokens)
    layer_stats["L1 hit"] = int(layer_stats.get("layer1_dictionary_hits", 0))
    layer_stats["L2 vector used"] = int(layer_stats.get("layer2_vector_hits", 0))
    layer_stats["MRW fallback used"] = int(layer_stats.get("layer2_mrw_fallback_used", 0))
    layer_stats["Final resolved"] = int(layer_stats.get("layer3_final_resolved", 0))

    return {
        "source_text": text,
        "tokens": tagged_tokens,
        "tokenizer": tokenizer,
        "tokenizer_mode": mode,
        "wsd": wsd_meta,
        "layers": layer_stats,
        "constraints": constraint_stats,
        "lemma_frequency": lemma_frequency,
        "domain_frequency": domain_frequency,
        "summary": summary,
    }


def main() -> None:
    args = parse_args()

    if args.gui:
        try:
            from src.gui.webview_app import launch_webview

            launch_webview()
        except ImportError:
            raise RuntimeError(
                "Legacy Tk GUI has been removed. Please run Electron desktop via run.bat."
            )
        return

    if not args.input and not args.text:
        raise ValueError("Either --input or --text must be provided.")

    if args.input and args.text:
        raise ValueError("Please provide only one of --input or --text.")

    if args.min_frequency < 1:
        raise ValueError("--min-frequency must be greater than or equal to 1.")

    if args.top_n is not None and args.top_n < 1:
        raise ValueError("--top-n must be greater than or equal to 1.")

    text = read_text_file(args.input) if args.input else args.text
    result = build_result(
        text=text,
        lexicon_path=args.lexicon,
        categories_path=args.categories,
        language=args.language,
        mode=args.mode,
        unknown_domain=args.unknown_domain,
        min_frequency=args.min_frequency,
        top_n=args.top_n,
        use_bert_wsd=not args.no_bert_wsd,
        bert_model_dir=args.bert_model_dir,
    )

    if args.bundle_dir:
        write_csv_bundle(result, Path(args.bundle_dir))
        return

    if args.output:
        output_path = Path(args.output)
        suffix = output_path.suffix.lower()

        if suffix == ".json":
            write_json(result, output_path)
        elif suffix == ".csv":
            write_csv(result, output_path)
        else:
            raise ValueError("Unsupported output format. Use .json or .csv")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
