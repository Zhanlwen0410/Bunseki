# Bunseki — Electron desktop

## Prereqs

- Node.js 18+ and npm
- Python env with `pip install -r ../requirements.txt` (SudachiPy + FastAPI stack)

## Dev

```bash
npm install
npm run dev
```

This runs Vite on `http://127.0.0.1:5173`, watches Electron `main`/`preload`, and starts Electron. The main process spawns:

`python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8765`

Override with `WMIX_PYTHON` / `WMIX_API_PORT` if needed.

## If `npm install` stalls or `node_modules` is incomplete

Delete `node_modules` and run `npm install` again (first install downloads Electron binaries and can take several minutes).

## Production-ish build

```bash
npm run build
npm start
```

`npm start` expects `dist/` (Vite) and `dist-electron/*.cjs` to exist; run `npm run build` first.
