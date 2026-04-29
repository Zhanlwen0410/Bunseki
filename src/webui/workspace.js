import { $, renderSummary, renderTable, setStatus } from "./ui.js";

export function renderWorkspace(state) {
  if (!state.result) return;
  renderSummary(state.result.summary);

  renderTable(
    "#tokens-table",
    [
      { key: "surface", label: "Surface" },
      { key: "lemma", label: "Lemma" },
      { key: "pos", label: "POS" },
      { key: "domain_code", label: "Domain" },
    ],
    state.result.tokens,
    (index) => {
      const row = state.result.tokens[index];
      state.selectedKeyword = row.lemma;
      state.selectedDomain = row.domain_code;
      $("#kwic-keyword").value = state.selectedKeyword;
      $("#kwic-domain").value = state.selectedDomain;
      setStatus(`${row.lemma} / ${row.domain_code}`);
    },
  );

  renderTable(
    "#lemmas-table",
    [
      { key: "lemma", label: "Lemma" },
      { key: "count", label: "Freq" },
    ],
    Object.entries(state.result.lemma_frequency).map(([lemma, count]) => ({ lemma, count })),
    (index) => {
      const row = Object.entries(state.result.lemma_frequency)[index];
      state.selectedKeyword = row[0];
      $("#kwic-keyword").value = state.selectedKeyword;
    },
  );

  renderTable(
    "#domains-table",
    [
      { key: "domain_code", label: "Domain" },
      { key: "count", label: "Freq" },
    ],
    Object.entries(state.result.domain_frequency).map(([domain_code, count]) => ({ domain_code, count })),
    (index) => {
      const row = Object.entries(state.result.domain_frequency)[index];
      state.selectedDomain = row[0];
      $("#kwic-domain").value = state.selectedDomain;
    },
  );
}
