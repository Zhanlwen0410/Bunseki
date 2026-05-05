# Bunseki

> ⚠️ **Repository Status: Outdated Early Prototype**
>
> This repository contains an early-stage version of the Bunseki system and is no longer actively maintained.
>
> The current development has significantly progressed beyond what is presented here, with major improvements in architecture, semantic mapping, and overall system design.
>
> This codebase is kept for reference purposes only and does not reflect the latest implementation.

Bunseki is a Japanese MIPVU metaphor analysis system with a desktop GUI and CLI. It performs semantic domain tagging using a USAS-style category system (A1–Z99) and identifies metaphorical expressions via a 3-layer pipeline with optional LLM-based source/target domain classification.

## Features

- **Desktop GUI:** Electron + React + TypeScript + Material-UI, launched from `run.bat` (Vite + Electron + local Python FastAPI)
- **3-layer semantic pipeline:** L1 (dictionary/WordNet) → L2 (vector similarity + MRW fallback) → L3 (adjudication + LLM-MIPVU)
- **MIPVU metaphor detection:** BERT cosine distance between basic and contextual meaning, POS-specific thresholds
- **LLM MIPVU layer (optional):** LLM confirms MRW, refines source domain, and identifies target domain via multiple-choice prompts (DeepSeek/OpenAI/Gemini/Claude/local)
- **SQLite LLM cache:** identical inputs skip API calls via MD5 hash keys
- SudachiPy tokenization and lemmatization with POS tagging
- Chinese, Japanese, English UI switching
- Project save/open, single-text analysis, dual-text comparison
- KWIC view, semantic profile (bar chart + D3 network), lexicon editor
- Export as JSON, CSV, or CSV bundle

## Architecture

```
bunseki.py              # Unified entry point → src.main.main
config/settings.py      # Centralized config (env vars + data/llm_config.json)
llm/                    # LLM client layer (router + 4 providers + SQLite cache)
  base.py               #   Abstract LLMClient (3 methods, multiple-choice only)
  router.py             #   Fallback chain + MD5 cache
src/
  main.py               # build_result() — core 3-layer pipeline
  semantic/tagger.py    # Semantic tagger (WordNet mapping + vector search)
  metaphor/mrw.py       # MRW encoder (BERT cosine distance)
  api/server.py         # FastAPI endpoints (analyze, kwic, lexicon, LLM config, etc.)
  analysis/             # Domain profile, context detail, comparison
  statistics/           # Frequency, domain stats, summary
  services/             # Analysis service layer
  utils/                # File I/O, category labels
desktop/                # Electron + React desktop app
data/
  lexicon.json          # Domain-code → words lexicon
  usas_categories.json  # USAS category table (A1–Z99, ja/en labels)
  llm_config.json       # LLM provider + masked API keys (written by Settings UI)
  jmdict/               # JMdict Japanese dictionary data
  wordnet/wnjpn.db      # Japanese WordNet SQLite database
  mapping/              # WordNet→USAS static maps
```

Deprecated modules (retained for reference): `cli/`, `pipeline/`, `mapper/`, `disambiguator/`, `analyzer/`, `evaluation/`, `src/llm/mipvu.py`

## Installation

1. Install Python 3.10+ with SudachiPy.
2. Install Node.js 18+ (required for Electron desktop).
3. Install core dependencies:

```
py -m pip install -r requirements.txt
```

4. The first `run.bat` launch runs `npm install` inside `desktop/` automatically.

Optional LLM dependencies (install manually as needed):

```
pip install openai>=1.0,<2.0          # DeepSeek / OpenAI
pip install google-generativeai>=0.8   # Gemini
pip install anthropic>=0.30           # Claude
# pip install llama-cpp-python         # Local offline LLM
```

## GUI Usage (Electron)

1. Double-click `run.bat` (or `cd desktop && npm run dev`).
2. Electron starts a local API on `127.0.0.1:8765`.
3. Paste Japanese text into the workspace editor and click **Analyze**.
4. Navigate via sidebar: **Workspace**, **Semantic profile**, **KWIC**, **Lexicon**, **Compare**.

### LLM Configuration (Settings Page)

Open **Settings** to configure the LLM-MIPVU pipeline:

- **Provider:** Select `none` / `deepseek` / `openai` / `gemini` / `claude` / `local`
- **API Keys:** Enter keys for each provider (masked display, `****` preserves existing values)
- **Fallback Chain:** Comma-separated provider list tried in order on failure
- **Local Model Path:** Path to a GGUF model file (when provider = `local`)
- A green/orange indicator shows whether at least one provider is configured

API keys can also be set via environment variables:
- `BUNSEKI_LLM_PROVIDER`, `BUNSEKI_DEEPSEEK_API_KEY`, `BUNSEKI_OPENAI_API_KEY`, `BUNSEKI_GEMINI_API_KEY`, `BUNSEKI_ANTHROPIC_API_KEY`, `BUNSEKI_LOCAL_MODEL_PATH`

Environment (optional):
- `WMIX_API_PORT` — API port (default `8765`)
- `WMIX_PYTHON` — Python executable (default `python`)

## CLI Usage

```
py bunseki.py --text "彼女の言葉は刃のように刺さった。" --language ja
py bunseki.py --input sample.txt --output result.json --language ja
py bunseki.py --input sample.txt --bundle-dir output_csv --mode A --top-n 20
```

Options: `--language zh|ja|en`, `--mode A|B|C` (Sudachi mode), `--min-frequency N`, `--top-n N`, `--no-bert-wsd`, `--bert-model-dir PATH`

Run the API server standalone:

```
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8765
```

Quick smoke test:

```
python scripts/smoke_api.py
```

## MIPVU Pipeline

### How metaphor detection works

1. **L1 — Basic sense lookup:** JMdict gloss + static WordNet→USAS mapping provides a basic meaning and source domain label for each content word.
2. **L2 — Semantic adjudication:** The SemanticPipeline scores candidate domains via vector similarity; if vector search fails, it falls back to MRW-based candidates.
3. **MRW distance:** BERT embeddings encode the basic meaning and the context sentence; cosine distance between them measures metaphorical divergence. Each POS tag has its own threshold (e.g., 名詞=0.35, 動詞=0.25).
4. **L3 — LLM MIPVU (when configured):** For tokens exceeding the MRW threshold, the LLM confirms the metaphor, refines the source domain, and identifies the target domain. All prompts are multiple-choice (A/B/C) to prevent hallucination. Results are cached via MD5.

### Output fields

Each token includes: `domain_code`, `mrw_distance`, `is_metaphor_candidate`, `is_metaphor`, `source_domain`, `target_domain`, `target_domain_label`, `mipvu_path`, `confidence`, `pipeline_source`

## Desktop Packaging

From `desktop/`:

```
npm run dist:dir     # unpacked app → desktop/release/win-unpacked
npm run dist:win     # Windows installer (NSIS)
```

## Batch Lexicon Import

The lexicon editor supports: one term per line, `DOMAIN<TAB>TERM`, `DOMAIN,TERM`, `DOMAIN:TERM`, or full `.json` lexicon import.

## Data Files

| File | Purpose |
|------|---------|
| `data/lexicon.json` | Domain code → words lexicon |
| `data/usas_categories.json` | USAS category table (A1–Z99, ja/en labels) |
| `data/llm_config.json` | LLM provider + masked API keys |
| `data/llm_cache.db` | SQLite cache for LLM responses |
| `data/jmdict/` | JMdict Japanese dictionary data |
| `data/wordnet/wnjpn.db` | Japanese WordNet SQLite database |
| `data/mapping/wordnet_usas_map.json` | Lemma-level WordNet → USAS mapping |
| `data/mapping/wn_pwn_usas_map.json` | Synset-level WordNet → USAS mapping |
| `data/mapping/semantic_constraints.json` | Token filter + candidate constraints |
| `data/mapping/basic_lemma_domain.json` | Per-lemma high-confidence domain anchors |
| `data/recent_files.json` | GUI recent-file cache |
