import { $ } from "./ui.js";
import { apiAnalyze, apiBootstrap } from "./api.js";
import { renderWorkspace } from "./workspace.js";
import { renderProfile } from "./profile.js";
import { setStatus, setUiBusy } from "./ui.js";

export async function analyze(state, refreshKwic) {
  setUiBusy(true);
  try {
    setStatus("Analyzing...");
    const payload = {
      text: $("#input-text").value,
      language: $("#language").value,
      mode: $("#mode").value,
      min_frequency: Number($("#min-frequency").value || 1),
    };
    const data = await apiAnalyze(payload);
    if (!data.ok) {
      const e = data.error || {};
      setStatus([e.message, e.hint].filter(Boolean).join(" ? "));
      return;
    }
    state.result = data.result;
    state.profile = data.profile;
    renderWorkspace(state);
    renderProfile(state, refreshKwic);
    setStatus(`Analyzed ${state.result.summary.token_count} tokens`);
  } catch (error) {
    setStatus(error.message || String(error));
  } finally {
    setUiBusy(false);
  }
}

export async function bootstrap(refreshLexicon) {
  const info = await apiBootstrap();
  $("#input-text").value = info.sample_text || "";
  $("#help-text").textContent = info.help || "";
  await refreshLexicon();
}
