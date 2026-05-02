import json
from pathlib import Path

from disambiguator import Disambiguator
from model import BertEncoder


def _resolve_model_dir() -> str:
    for candidate in ("model", "models/bert-jp"):
        p = Path(candidate)
        if p.exists() and (p / "config.json").exists():
            return candidate
    raise FileNotFoundError("No local BERT model directory found: model, models/bert-jp")


def main() -> None:
    encoder = BertEncoder(_resolve_model_dir())
    # Example polysemy: "高い" -> A13 (degree/high) vs I1.3 (price/cost)
    domain_descriptions = {
        "A13": "Degree, height, level, extent",
        "I1.3": "Money, price, cost, expensive",
    }
    wsd = Disambiguator(encoder=encoder, domain_descriptions=domain_descriptions)

    candidates = ["A13", "I1.3"]
    examples = [
        "このビルはとても高い。",
        "このパソコンは値段が高い。",
    ]
    out = []
    for sentence in examples:
        chosen = wsd.disambiguate(context=sentence, candidates=candidates)
        out.append({"text": sentence, "candidates": candidates, "selected_domain": chosen})
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
