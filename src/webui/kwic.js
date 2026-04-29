import { $, escapeHtml, renderTable, setStatus, setUiBusy } from "./ui.js";
import { apiKwic } from "./api.js";

export async function refreshKwic(state) {
  const keyword = $("#kwic-keyword").value.trim();
  const domain = $("#kwic-domain").value.trim();
  if (!keyword) {
    setStatus("Enter a keyword before refreshing KWIC.");
    return;
  }
  if (!state.result) {
    setStatus("Run analysis first, then refresh KWIC.");
    return;
  }
  setUiBusy(true);
  try {
    state.kwicRows = await apiKwic(keyword, domain);
    renderTable(
      "#kwic-table",
      [
        { key: "line", label: "Line" },
        { key: "left", label: "Left Context" },
        { key: "key", label: "Key", render: (value) => `<mark>${escapeHtml(value)}</mark>` },
        { key: "right", label: "Right Context" },
      ],
      state.kwicRows,
      async (index) => {
        const row = state.kwicRows[index];
        $("#kwic-prev").textContent = row.previous || "";
        $("#kwic-current").innerHTML = escapeHtml(row.current || "").replaceAll(
          escapeHtml(row.key),
          `<mark>${escapeHtml(row.key)}</mark>`,
        );
        $("#kwic-next").textContent = row.next || "";
        setStatus(`${row.key} @ ${row.source_offset}`);
      },
    );
    setStatus(`KWIC: ${state.kwicRows.length} line(s)`);
  } catch (error) {
    setStatus(error.message || String(error));
  } finally {
    setUiBusy(false);
  }
}
