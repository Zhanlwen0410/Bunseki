import { $, renderTable, setStatus, setUiBusy } from "./ui.js";
import { apiAddLexiconTerms, apiLexiconOverview } from "./api.js";

export async function refreshLexicon() {
  setUiBusy(true);
  try {
    const overview = await apiLexiconOverview();
    renderTable(
      "#lexicon-domains-table",
      [
        { key: "domain_code", label: "Domain" },
        { key: "domain_label", label: "Label" },
        { key: "count", label: "Count" },
      ],
      overview.domains,
      (index) => {
        const row = overview.domains[index];
        $("#lexicon-domain-code").value = row.domain_code;
        $("#lexicon-lemma-batch").value = (row.words || []).slice(0, 20).join("\n");
      },
    );
    setStatus("Lexicon overview loaded");
  } catch (error) {
    setStatus(error.message || String(error));
  } finally {
    setUiBusy(false);
  }
}

export async function importLexicon() {
  const domainCode = $("#lexicon-domain-code").value.trim();
  const lines = $("#lexicon-lemma-batch")
    .value.split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!domainCode) {
    setStatus("Select or enter a domain code before importing.");
    return;
  }
  if (!lines.length) {
    setStatus("Enter at least one lemma line to import.");
    return;
  }
  const payload = lines.map((lemma) => ({ domain_code: domainCode, lemma }));
  setUiBusy(true);
  try {
    const result = await apiAddLexiconTerms(payload);
    if (!result.ok) {
      const e = result.error || {};
      setStatus([e.message, e.hint].filter(Boolean).join(" ? "));
      return;
    }
    let msg = `Imported ${result.added} lemma(s)`;
    if (result.warning) msg += `. ${result.warning}`;
    setStatus(msg);
    await refreshLexicon();
  } catch (error) {
    setStatus(error.message || String(error));
  } finally {
    setUiBusy(false);
  }
}
