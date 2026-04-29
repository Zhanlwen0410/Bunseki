import { state } from "./state.js";
import { $, $$, switchTab, switchView } from "./ui.js";
import { analyze, bootstrap } from "./analysis.js";
import { importLexicon, refreshLexicon } from "./lexicon.js";
import { refreshKwic } from "./kwic.js";

document.addEventListener("DOMContentLoaded", async () => {
  $$(".nav-btn").forEach((btn) => btn.addEventListener("click", () => switchView(btn.dataset.view)));
  $$(".tab-btn").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
  $("#analyze-btn").addEventListener("click", () => analyze(state, () => refreshKwic(state)));
  $("#kwic-refresh").addEventListener("click", () => refreshKwic(state));
  $("#lexicon-import-btn").addEventListener("click", importLexicon);
  await bootstrap(refreshLexicon);
});
