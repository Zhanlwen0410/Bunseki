import json
from pathlib import Path

from analyzer import DomainAnalyzer
from disambiguator import Disambiguator
from mapper import WordNetUSASMapper
from model import BertEncoder
from pipeline import Pipeline
from src.utils.file_io import read_json_file
from tokenizer import JapaneseTokenizer


def _model_dir() -> str:
    if (
        Path("models/bert-jp/config.json").exists()
        and (
            Path("models/bert-jp/pytorch_model.bin").exists()
            or Path("models/bert-jp/model.safetensors").exists()
        )
    ):
        return "models/bert-jp"
    if (
        Path("model/config.json").exists()
        and (Path("model/pytorch_model.bin").exists() or Path("model/model.safetensors").exists())
    ):
        return "model"
    raise FileNotFoundError("No local BERT model directory found: models/bert-jp, model")


def run_demo() -> None:
    text = "先生は学校で研究の話をして、ご飯を食べる。"
    cats = read_json_file("data/usas_categories.json")
    descriptions = {
        code: str((value or {}).get("en", "")).strip()
        for code, value in cats.items()
        if isinstance(code, str) and isinstance(value, dict)
    }
    mapper = WordNetUSASMapper("data/mapping/wordnet_usas_map.json")
    pipeline = Pipeline(
        tokenizer=JapaneseTokenizer(tokenizer="sudachi", mode="C"),
        mapper=mapper,
        disambiguator=Disambiguator(
            BertEncoder(_model_dir()),
            domain_descriptions=descriptions,
            labeled_lexicon=mapper.labeled_lexicon(),
        ),
        analyzer=DomainAnalyzer(),
    )
    result = pipeline.run(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_demo()
