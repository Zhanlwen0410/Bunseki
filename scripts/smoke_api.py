"""Minimal regression smoke checks for local FastAPI endpoints.

Usage:
  python scripts/smoke_api.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8765"


def get_json(path: str) -> Any:
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, payload: dict[str, Any], timeout: float = 20.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def wait_health(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            data = get_json("/health")
            if data.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError("API health check timeout.")


def main() -> int:
    required_modules = ("sudachipy", "fastapi", "uvicorn")
    missing: list[str] = []
    for name in required_modules:
        try:
            __import__(name)
        except ModuleNotFoundError:
            missing.append(name)
    if missing:
        print(
            "Smoke check blocked: missing Python modules: "
            + ", ".join(missing)
            + "\n"
            "Install with: python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
    ]
    proc = subprocess.Popen(uvicorn_cmd, cwd=str(REPO_ROOT))
    try:
        wait_health()

        bootstrap = get_json("/bootstrap")
        assert "lexicon_path" in bootstrap

        analyze = post_json(
            "/analyze",
            {
                "text": "彼女の言葉は刃のように刺さった。学校へ行く。he is here.",
                "language": "ja",
                "mode": "C",
                "min_frequency": 1,
                "use_bert_wsd": False,
            },
            timeout=90.0,
        )
        assert analyze.get("ok") is True, analyze
        result = analyze["result"]
        assert result.get("summary", {}).get("token_count", 0) > 0, result
        tokens = result.get("tokens", [])
        assert isinstance(tokens, list) and tokens, result
        # 3-layer pipeline schema + metrics checks.
        assert any("basic_meaning" in t for t in tokens), "missing basic_meaning in tokens"
        assert any("source_domain_label" in t for t in tokens), "missing source_domain_label in tokens"
        assert all("mrw_distance" in t for t in tokens), "missing mrw_distance on some token"
        assert all("is_metaphor_candidate" in t for t in tokens), "missing is_metaphor_candidate on some token"
        assert all(len(t.get("mrw_candidates", [])) <= 3 for t in tokens if isinstance(t.get("mrw_candidates"), list))
        assert any(isinstance(t.get("scores_by_domain"), dict) and t.get("scores_by_domain") for t in tokens), (
            "missing adjudication scores"
        )
        layers = result.get("layers", {})
        assert int(layers.get("L2 vector used", 0)) > 0, layers
        school = next((t for t in tokens if str(t.get("surface", "")) == "学校"), None)
        if school is not None:
            assert str(school.get("domain_code", "")) != "S9", school
        pronoun = next((t for t in tokens if str(t.get("surface", "")).lower() == "he"), None)
        if pronoun is not None:
            assert not str(pronoun.get("domain_code", "")).startswith("B1"), pronoun

        profile = get_json("/domain-profile?language=ja")
        assert profile.get("ok") is True, profile

        kwic = post_json("/kwic", {"keyword": "smoke", "domain_code": ""})
        if isinstance(kwic, dict):
            assert kwic.get("ok") is True, kwic
            assert isinstance(kwic.get("data"), list), kwic
        else:
            assert isinstance(kwic, list)

        domain_words = get_json("/domain-words/Z99")
        assert domain_words.get("ok") is True, domain_words
        assert isinstance(domain_words.get("data"), list), domain_words

        lexicon_overview = get_json("/lexicon/overview")
        assert "domains" in lexicon_overview

        compare = post_json(
            "/compare",
            {
                "left_text": "left text for compare endpoint",
                "right_text": "right text for compare endpoint",
                "language": "ja",
                "mode": "C",
                "min_frequency": 1,
            },
        )
        assert compare.get("ok") is True, compare

        print("Smoke check passed: /health /bootstrap /analyze /domain-profile /kwic /lexicon/overview /compare")
        return 0
    except (AssertionError, TimeoutError, urllib.error.URLError) as exc:
        print(f"Smoke check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
