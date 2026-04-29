export const $ = (selector) => document.querySelector(selector);
export const $$ = (selector) => Array.from(document.querySelectorAll(selector));

export function setStatus(message) {
  $("#status").textContent = message;
}

export function setUiBusy(busy) {
  const ids = ["#analyze-btn", "#kwic-refresh", "#lexicon-import-btn"];
  ids.forEach((sel) => {
    const el = $(sel);
    if (el) el.disabled = busy;
  });
}

export function switchView(view) {
  $$(".nav-btn").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
  $$(".view").forEach((panel) => panel.classList.toggle("active", panel.id === `view-${view}`));
}

export function switchTab(name) {
  $$(".tab-btn").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === name));
  $$(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${name}`));
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

export function renderTable(target, columns, rows, onClick) {
  const table = $(target);
  const thead = `<thead><tr>${columns.map((column) => `<th>${column.label}</th>`).join("")}</tr></thead>`;
  const tbody = rows.map((row, index) => {
    const cells = columns
      .map((column) => `<td>${column.render ? column.render(row[column.key], row) : escapeHtml(row[column.key] ?? "")}</td>`)
      .join("");
    return `<tr data-index="${index}">${cells}</tr>`;
  }).join("");
  table.innerHTML = `${thead}<tbody>${tbody}</tbody>`;
  if (onClick) {
    table.querySelectorAll("tbody tr").forEach((row) => row.addEventListener("click", () => onClick(Number(row.dataset.index))));
  }
}

export function renderSummary(summary = {}) {
  const strip = $("#summary-strip");
  strip.innerHTML = Object.entries(summary)
    .slice(0, 6)
    .map(([key, value]) => `<span class="stat-pill">${escapeHtml(key)}: ${escapeHtml(value)}</span>`)
    .join("");
}
