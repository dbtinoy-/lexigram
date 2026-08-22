/* Vanilla-JS client for the prompt lab (no build step). */
"use strict";

let variant = "v1";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

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
  const vars = { issue: $("issue").value, tone: $("tone").value };
  const payload = { variant, vars };
  const revRaw = $("rev").value.trim();
  if (revRaw) payload.rev = Number(revRaw);

  const res = await fetch("/api/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) return showError((await res.json()).error);
  $("preview").textContent = (await res.json()).rendered;
}

async function loadHistory() {
  const res = await fetch(`/api/history/${variant}`);
  if (!res.ok) {
    $("history-list").innerHTML = "<li class='muted'>unknown variant</li>";
    return;
  }
  const { entries } = await res.json();
  $("history-list").innerHTML = entries
    .map((e) => `<li>rev ${e.rev}${e.current ? " ← active" : ""}</li>`)
    .join("");
}

async function rollback() {
  hide("error");
  const res = await fetch("/api/rollback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variant }),
  });
  if (!res.ok) return showError((await res.json()).error);
  await loadHistory();
  await renderPreview();
}

async function runAb() {
  hide("error");
  const res = await fetch("/api/ab", { method: "POST" });
  if (!res.ok) return showError((await res.json()).error);
  const report = await res.json();
  $("ab-body").innerHTML = Object.entries(report.variants)
    .map(([key, v]) =>
      `<tr><td>${key}</td><td>${v.average_score}</td><td>${v.passed}/${v.total}</td></tr>`)
    .join("");
  $("winner").textContent = `winner: ${report.winner}`;
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
