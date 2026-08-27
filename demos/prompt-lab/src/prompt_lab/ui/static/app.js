/* Vanilla-JS client for the prompt lab (no build step). */
"use strict";

let variant = "v1";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || body.detail || res.statusText);
  }
  return res.json();
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
  try {
    const vars = { issue: $("issue").value, tone: $("tone").value };
    const payload = { variant, vars };
    const revRaw = $("rev").value.trim();
    if (revRaw) payload.rev = Number(revRaw);
    const data = await api("/api/render", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("preview").textContent = data.rendered;
  } catch (e) {
    showError(e.message);
  }
}

async function loadHistory() {
  try {
    const { entries } = await api(`/api/history/${variant}`);
    $("history-list").innerHTML = entries
      .map((e) => `<li>rev ${e.rev}${e.current ? " ← active" : ""}</li>`)
      .join("");
  } catch {
    $("history-list").innerHTML = "<li class='muted'>unknown variant</li>";
  }
}

async function rollback() {
  hide("error");
  try {
    await api("/api/rollback", {
      method: "POST",
      body: JSON.stringify({ variant }),
    });
    await loadHistory();
    await renderPreview();
  } catch (e) {
    showError(e.message);
  }
}

async function runAb() {
  hide("error");
  try {
    const report = await api("/api/ab", { method: "POST" });
    $("ab-body").innerHTML = Object.entries(report.variants)
      .map(([key, v]) =>
        `<tr><td>${key}</td><td>${v.average_score}</td><td>${v.passed}/${v.total}</td></tr>`)
      .join("");
    $("winner").textContent = `winner: ${report.winner}`;
  } catch (e) {
    showError(e.message);
  }
}

document.querySelectorAll("#variants button").forEach((b) =>
  b.addEventListener("click", () => {
    variant = b.dataset.variant;
    setActiveVariant();
    loadHistory();
    renderPreview();
  }));
$("preview-form").addEventListener("submit", renderPreview);
$("rollback-btn").addEventListener("click", rollback);
$("ab-btn").addEventListener("click", runAb);
setActiveVariant();
loadHistory();
renderPreview();
