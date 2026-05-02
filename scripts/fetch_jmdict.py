"""Download and install JMdict locally (JMdict_e.xml).

Usage (from repo root):
  python scripts/fetch_jmdict.py

Source:
  EDRDG public archive (ftp.edrdg.org)
"""

from __future__ import annotations

import gzip
import shutil
import sys
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "jmdict"
GZ_PATH = OUT_DIR / "JMdict_e.gz"
XML_PATH = OUT_DIR / "JMdict_e.xml"

# HTTP is more universally accessible than FTP in many environments.
JM_DICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz"


def download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "bunseki-fetch/1.0"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        with out_path.open("wb") as f:
            shutil.copyfileobj(resp, f)


def gunzip(src: Path, dst: Path) -> None:
    with gzip.open(src, "rb") as f_in:
        with dst.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def main() -> int:
    try:
        print(f"Downloading: {JM_DICT_URL}")
        download(JM_DICT_URL, GZ_PATH)
        print(f"Saved: {GZ_PATH} ({GZ_PATH.stat().st_size} bytes)")
        print(f"Decompressing to: {XML_PATH}")
        gunzip(GZ_PATH, XML_PATH)
        print(f"Installed: {XML_PATH} ({XML_PATH.stat().st_size} bytes)")
        return 0
    except Exception as exc:
        print(f"fetch_jmdict failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

