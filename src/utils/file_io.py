from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict


def read_text_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def read_json_file(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    tmp_path.replace(output_path)


def write_csv(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "record_type",
                "surface",
                "lemma",
                "pos",
                "domain_code",
                "domain_label",
                "key",
                "count",
            ],
        )
        writer.writeheader()

        for token in data.get("tokens", []):
            writer.writerow(
                {
                    "record_type": "token",
                    "surface": token.get("surface", ""),
                    "lemma": token.get("lemma", ""),
                    "pos": token.get("pos", ""),
                    "domain_code": token.get("domain_code", ""),
                    "domain_label": token.get("domain_label", ""),
                    "key": "",
                    "count": "",
                }
            )

        for lemma, count in data.get("lemma_frequency", {}).items():
            writer.writerow(
                {
                    "record_type": "lemma_frequency",
                    "surface": "",
                    "lemma": "",
                    "pos": "",
                    "domain_code": "",
                    "domain_label": "",
                    "key": lemma,
                    "count": count,
                }
            )

        for domain, count in data.get("domain_frequency", {}).items():
            writer.writerow(
                {
                    "record_type": "domain_frequency",
                    "surface": "",
                    "lemma": "",
                    "pos": "",
                    "domain_code": domain,
                    "domain_label": "",
                    "key": domain,
                    "count": count,
                }
            )

        summary = data.get("summary", {})
        for key, value in summary.items():
            writer.writerow(
                {
                    "record_type": "summary",
                    "surface": "",
                    "lemma": "",
                    "pos": "",
                    "domain_code": "",
                    "domain_label": "",
                    "key": key,
                    "count": value,
                }
            )


def write_csv_bundle(data: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "tokens.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["surface", "lemma", "pos", "domain_code", "domain_label"]
        )
        writer.writeheader()
        writer.writerows(data.get("tokens", []))

    with (output_dir / "lemma_frequency.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["lemma", "count"])
        writer.writeheader()
        for lemma, count in data.get("lemma_frequency", {}).items():
            writer.writerow({"lemma": lemma, "count": count})

    with (output_dir / "domain_frequency.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["domain_code", "count"])
        writer.writeheader()
        for domain, count in data.get("domain_frequency", {}).items():
            writer.writerow({"domain_code": domain, "count": count})

    with (output_dir / "summary.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "value"])
        writer.writeheader()
        for key, value in data.get("summary", {}).items():
            writer.writerow({"metric": key, "value": value})


def read_recent_files(file_path: Path) -> Dict[str, list[str]]:
    if not file_path.exists():
        return {
            "recent_text_files": [],
            "recent_lexicon_files": [],
            "recent_project_files": [],
        }
    with file_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    payload.setdefault("recent_text_files", [])
    payload.setdefault("recent_lexicon_files", [])
    payload.setdefault("recent_project_files", [])
    return payload


def write_recent_files(file_path: Path, payload: Dict[str, list[str]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def push_recent_file(items: list[str], value: str, limit: int = 10) -> list[str]:
    normalized = [item for item in items if item != value]
    normalized.insert(0, value)
    return normalized[:limit]
