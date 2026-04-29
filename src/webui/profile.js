import { $, escapeHtml, renderTable, setStatus, switchView } from "./ui.js";
import { apiDomainWords } from "./api.js";

export function renderProfile(state, refreshKwic) {
  renderTable(
    "#profile-table",
    [
      { key: "domain_code", label: "Domain" },
      { key: "frequency", label: "Freq" },
      { key: "relative_per_10k", label: "Per 10k" },
    ],
    state.profile,
    async (index) => {
      const row = state.profile[index];
      state.selectedDomain = row.domain_code;
      try {
        const words = await apiDomainWords(row.domain_code);
        state.domainWords = words;
        $("#profile-summary").innerHTML = `
      <div><strong>${escapeHtml(row.domain_code)}</strong></div>
      <div>${escapeHtml(row.domain_label)}</div>
      <div>${escapeHtml(row.description)}</div>
      <div>Types / Tokens: ${escapeHtml(row.types)} / ${escapeHtml(row.tokens)}</div>
      <div>Per 10k: ${escapeHtml(row.relative_per_10k)}</div>
    `;
        renderTable(
          "#domain-words-table",
          [
            { key: "word", label: "Word" },
            { key: "lemma", label: "Lemma" },
            { key: "frequency", label: "Freq" },
            { key: "relative_per_10k", label: "Per 10k" },
          ],
          words,
          async (wordIndex) => {
            const wordRow = words[wordIndex];
            state.selectedKeyword = wordRow.lemma;
            $("#kwic-keyword").value = wordRow.lemma;
            $("#kwic-domain").value = state.selectedDomain;
            switchView("kwic");
            await refreshKwic();
          },
        );
      } catch (error) {
        setStatus(error.message || String(error));
      }
    },
  );
}
