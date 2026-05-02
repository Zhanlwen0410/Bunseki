# DEPRECATED: This module is superseded by src/main.py.
# It is retained for reference only and will be removed in a future version.

import argparse
import json
from pathlib import Path

from analyzer import DomainAnalyzer
from disambiguator import Disambiguator
from mapper import WordNetUSASMapper
from model import BertEncoder
from pipeline import Pipeline
from tokenizer import JapaneseTokenizer
from src.utils.file_io import read_json_file


def resolve_model_dir(cli_value: str) -> str:
    def _is_valid_model_dir(path: Path) -> bool:
        if not path.exists() or not path.is_dir():
            return False
        has_config = (path / "config.json").exists()
        has_weights = (path / "pytorch_model.bin").exists() or (path / "model.safetensors").exists()
        has_tokenizer = (path / "tokenizer_config.json").exists() or (path / "vocab.txt").exists()
        return has_config and has_weights and has_tokenizer

    if cli_value and _is_valid_model_dir(Path(cli_value)):
        return cli_value
    for candidate in ("model", "models/bert-jp"):
        if _is_valid_model_dir(Path(candidate)):
            return candidate
    raise FileNotFoundError(
        "No local BERT model directory found. Checked: models/bert-jp, model"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bunseki")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze Japanese text")
    analyze.add_argument("input", type=str, help="Input text file path")
    analyze.add_argument(
        "--mapping",
        default="data/mapping/wordnet_usas_map.json",
        help="WordNet->USAS mapping file path",
    )
    analyze.add_argument(
        "--model-dir",
        default="model",
        help="Local BERT directory (default: model)",
    )
    analyze.add_argument("--tokenizer", default="sudachi", choices=["sudachi", "mecab", "chasen"])
    analyze.add_argument("--mode", default="C", choices=["A", "B", "C"])
    analyze.add_argument("--output", default="", help="Optional output json path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command != "analyze":
        raise ValueError(f"Unsupported command: {args.command}")

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            "Use an existing path (e.g., sample.txt) or provide an absolute path."
        )
    text = input_path.read_text(encoding="utf-8")
    tokenizer = JapaneseTokenizer(tokenizer=args.tokenizer, mode=args.mode)
    mapper = WordNetUSASMapper(mapping_path=args.mapping)
    encoder = BertEncoder(model_dir=resolve_model_dir(args.model_dir))
    cats = read_json_file("data/usas_categories.json")
    descriptions = {
        code: str((value or {}).get("en", "")).strip()
        for code, value in cats.items()
        if isinstance(code, str) and isinstance(value, dict)
    }
    disambiguator = Disambiguator(
        encoder=encoder,
        domain_descriptions=descriptions,
        labeled_lexicon=mapper.labeled_lexicon(),
    )
    analyzer = DomainAnalyzer()
    pipeline = Pipeline(tokenizer, mapper, disambiguator, analyzer)
    result = pipeline.run(text)

    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
