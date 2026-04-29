# Bunseki

Bunseki is a Python desktop and CLI tool for Japanese semantic domain analysis. It uses SudachiPy for tokenization and lemmatization, and applies a USAS-style semantic domain system based on the Wmatrix/UCREL tagset.

## Features

- **Desktop GUI (default):** Electron 28 + React 18 + TypeScript + Material-UI, launched from `run.bat` (starts Vite + Electron and spawns a local **Python FastAPI** process).
- **Legacy Tk GUI:** `run_legacy.bat` → `main.py --gui --gui-mode tk` (deprecated path; kept for migration).
- Workbench-style GUI with sidebar navigation and a unified analysis workspace
- Focused Japanese-only modules: text workspace, semantic profile, KWIC, lexicon center, compare view, and help
- Japanese tokenization and lemmatization with SudachiPy
- POS tagging for each token
- Full local USAS-style category table from `A1` to `Z99`
- Semantic domain tagging with `domain_code + domain_label`
- Chinese, Japanese, and English UI switching
- Project save/open support
- Single-text analysis with token, lemma, and domain tables
- Dual-text comparison for lemma and domain frequency differences
- Standard KWIC view with left context, key, right context, and sentence preview
- Cross-tool target flow: selecting a token, lemma, or domain updates the current target
- Semantic tagging helper that imports new lexicon entries using lemma form
- Batch lexicon import from pasted text, `.txt`, `.csv`, or `.json`
- Export as JSON, CSV, or a bundle of CSV files

## Author Details

- Organization: School of Foreign Languages, Xinjiang University
- Author: Zhang Wenze
- License: CC BY-NC-ND 4.0

![CC BY-NC-ND 4.0](image/by-nc-nd.svg)

## Data Files

- `data/lexicon.json`: domain-code-to-words lexicon
- `data/lexicon_wlsp_usas.json`: generated lexicon mapped from WLSP into USAS
- `data/wlsp_to_usas_map.json`: editable WLSP -> USAS mapping seed
- `data/wlsp_mapping_report.json`: coverage report for the WLSP mapping run
- `data/wlsp_usas_catalog.json`: row-level WLSP to USAS catalog
- `data/usas_categories.json`: full local USAS-style category table
- `data/recent_files.json`: GUI recent-file cache
- `data/WLSP-master`: local WLSP source files from the National Institute for Japanese Language and Linguistics data release

## Installation

1. Install **Python 3.10+** with SudachiPy (see `requirements.txt`).
2. Install **Node.js 18+** (required for the Electron desktop).
3. Open a terminal in the project directory and install Python deps:

`py -m pip install -r requirements.txt`

4. The first time you run the desktop, `run.bat` will run `npm install` inside `desktop/`.

## GUI Usage (Electron — default)

1. Double-click `run.bat` (or from a shell: `cd desktop` then `npm run dev`).
2. Electron starts a local API (`uvicorn src.api.server:app` on `127.0.0.1:8765` by default). Wait until the window loads.
3. Load Japanese text or paste it into the workspace editor.
4. Choose label language, Sudachi mode, and frequency filters.
5. Click **Analyze**.
6. Use the sidebar: **Workspace**, **Semantic profile**, **KWIC**, **Lexicon**, **Compare**.
7. In **Workspace**, after Analyze you can inspect token rows, lemma frequency, domain frequency, and click tokens to fetch context detail.

Environment (optional):

- `WMIX_API_PORT` — API port (default `8765`).
- `WMIX_PYTHON` — Python executable to spawn (default `python` on `PATH`).

## Legacy Tk GUI

1. Run `run_legacy.bat` (same Python/Sudachi requirements as before).

## GUI Usage (legacy Tk)

1. Double-click `run_legacy.bat` after `pip install -r requirements.txt`.
2. Load Japanese text or paste it into the workspace editor.
3. Choose UI language, Sudachi mode, and frequency filters.
4. Click Analyze.
5. Move between `Workbench`, `Semantic Profile`, `KWIC`, `Lexicon Center`, and `Compare` from the sidebar.
6. In `Semantic Profile`, click a domain to inspect its words and double-click a word to open KWIC.
7. In `KWIC`, inspect `Line | Left Context | Key | Right Context` and double-click a row to view the source context.
8. In `Lexicon Center`, add terms, batch import entries, or use the semantic tagger to write lemma-based entries into the lexicon.
9. Save the workspace as a project file when needed.

## Batch Lexicon Import

The lexicon editor supports:

- One term per line: each line will be added to the currently selected domain
- `DOMAIN<TAB>TERM`
- `DOMAIN,TERM`
- `DOMAIN:TERM`
- Full `.json` lexicon import

## WLSP Mapping Pipeline

The project can now use the local `WLSP-master` files as the original lexicon source and map them into the USAS semantic domain system.

### Build the WLSP-based lexicon

`py scripts/build_wlsp_lexicon.py`

This generates:

- `data/lexicon_wlsp_usas.json`
- `data/wlsp_mapping_report.json`
- `data/wlsp_usas_catalog.json`

The GUI and CLI will prefer `lexicon_wlsp_usas.json` automatically when it exists.

## CLI Usage

### Launch the GUI

- **Electron (default):** `run.bat` from the repo root.
- **Tk only:** `run_legacy.bat`.

### Run the Python API alone (debug)

From the repo root (with venv activated if you use one):

`python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8765`

### Minimal regression checklist

After major UI/API changes, verify these in order:

1. Analyze a short sentence in `Workspace` and confirm token/domain rows render.
2. Open `Semantic profile` and confirm both Plotly bar chart and D3 network render.
3. Open `KWIC`, search a lemma (e.g. `ご飯`), confirm rows are returned.
4. Open `Lexicon`, add one term, then re-open overview and confirm count updates.
5. Open `Compare`, input left/right texts, confirm domain and lemma deltas render.

Quick API smoke command (from repo root):

`python scripts/smoke_api.py`

### Desktop packaging (Electron builder)

From `desktop/`:

- `npm run dist:dir` - generate unpacked app in `desktop/release/win-unpacked`
- `npm run dist:win` - generate Windows installer (NSIS)
- If GitHub download is blocked in your network, use mirror variants:
  - `npm run dist:dir:cn`
  - `npm run dist:win:cn`

### Analyze a file

py main.py --input sample.txt --output result.json --language zh

### Analyze raw text

py main.py --text "Japanese text here" --output result.csv --language en

### Export multiple CSV files

py main.py --input sample.txt --bundle-dir output_csv --mode A --top-n 20

## Domain System

The project uses a local USAS-style category file based on the Wmatrix/UCREL semantic analysis approach. The complete local table includes codes such as:

- `A1` General and abstract terms
- `F1` Food
- `M1` Moving, coming and going
- `Q2` Speech acts
- `S2` People
- `X2.1` Thought, belief
- `Z99` Unmatched
