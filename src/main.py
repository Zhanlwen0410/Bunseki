import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing.tokenizer import BaseTokenizer, create_tokenizer
from src.semantic.tagger import SemanticTagger

# Process-local caches avoid reloading tokenizers + large lexicons on every analyze/KWIC pass.
_tokenizer_cache: dict[tuple[str, str], BaseTokenizer] = {}
_tagger_cache: dict[tuple[str, str, str, str], SemanticTagger] = {}
_tagger_mtimes: dict[str, float] = {}
from src.statistics.domain_stats import compute_domain_frequency
from src.statistics.frequency import compute_lemma_frequency
from src.statistics.summary import compute_summary
from src.utils.file_io import read_text_file, write_csv, write_csv_bundle, write_json


def default_lexicon_path() -> str:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    generated = data_dir / "lexicon_wlsp_usas.json"
    fallback = data_dir / "lexicon.json"
    return str(generated if generated.exists() else fallback)


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
        choices=["webview", "tk"],
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
    return parser.parse_args()


def _get_cached_tokenizer(tokenizer: str, mode: str) -> BaseTokenizer:
    key = ((tokenizer or "sudachi").strip().lower(), (mode or "C").strip().upper())
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
    _tagger_cache.clear()
    _tagger_mtimes.clear()
    _tokenizer_cache.clear()


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

    return {
        "source_text": text,
        "tokens": tagged_tokens,
        "tokenizer": tokenizer,
        "tokenizer_mode": mode,
        "lemma_frequency": lemma_frequency,
        "domain_frequency": domain_frequency,
        "summary": summary,
    }


def main() -> None:
    args = parse_args()

    if args.gui:
        if args.gui_mode == "webview":
            try:
                from src.gui.webview_app import launch_webview

                launch_webview()
            except ImportError:
                from src.gui.app import launch_gui

                launch_gui()
        else:
            from src.gui.app import launch_gui

            launch_gui()
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
