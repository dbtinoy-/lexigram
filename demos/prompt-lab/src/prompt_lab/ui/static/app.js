/* Vanilla-JS client for the prompt lab (no build step). */
"use strict";

let variant = "v1";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");
const escapeHtml = (value) => {
  const element = document.createElement("div");
  element.textContent = String(value);
  return element.innerHTML;
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.error || body.detail) {
    throw new Error(body.error || body.detail || res.statusText || `HTTP ${res.status}`);
  }
  return body;
}

function setActiveVariant() {
  document.querySelectorAll("#variants button").forEach((b) => {
    b.classList.toggle("active", b.dataset.variant === variant);
  });
}

function showError(message) {
  $("error").textContent = message;
  show("error");
}

async function renderPreview(event) {
  if (event) event.preventDefault();
  hide("error");
  const button = $("render-btn");
  button.disabled = true;
  button.textContent = "Rendering…";
  try {
    const vars = { issue: $("issue").value.trim(), tone: $("tone").value.trim() };
    const payload = { variant, vars };
    const revRaw = $("rev").value.trim();
    if (revRaw) payload.rev = Number(revRaw);
    const data = await api("/api/render", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("preview").textContent = data.rendered;
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Render";
  }
}

async function loadHistory() {
  try {
    const { entries } = await api(`/api/history/${variant}`);
    $("history-list").innerHTML = entries
      .map((entry) => `<li>rev ${escapeHtml(entry.rev)}${entry.current ? " ← active" : ""}</li>`)
      .join("");
  } catch (error) {
    $("history-list").innerHTML = "<li class='muted'>History unavailable</li>";
    showError(error.message);
  }
}

async function rollback() {
  hide("error");
  const button = $("rollback-btn");
  button.disabled = true;
  button.textContent = "Rolling back…";
  try {
    await api("/api/rollback", {
      method: "POST",
      body: JSON.stringify({ variant }),
    });
    await loadHistory();
    await renderPreview();
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Rollback";
  }
}

async function runAb() {
  hide("error");
  const button = $("ab-btn");
  button.disabled = true;
  button.textContent = "Scoring…";
  try {
    const report = await api("/api/ab", { method: "POST" });
    $("ab-body").innerHTML = Object.entries(report.variants)
      .map(([key, value]) =>
        `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(value.average_score)}</td>` +
        `<td>${value.passed}/${value.total}</td></tr>`)
      .join("");
    $("winner").textContent = `winner: ${escapeHtml(report.winner)}`;
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Run A/B";
  }
}

document.querySelectorAll("#variants button").forEach((button) =>
  button.addEventListener("click", async () => {
    variant = button.dataset.variant;
    setActiveVariant();
    await Promise.all([loadHistory(), renderPreview()]);
  }));
$("preview-form").addEventListener("submit", renderPreview);
$("rollback-btn").addEventListener("click", rollback);
$("ab-btn").addEventListener("click", runAb);
setActiveVariant();
loadHistory();
renderPreview();
