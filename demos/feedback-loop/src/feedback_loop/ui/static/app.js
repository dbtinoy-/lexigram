/* Vanilla-JS client for the feedback-loop console (no build step). */
"use strict";

let lastTrace = null;
const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

const KEYS = ["refund-policy", "shipping-time", "track-order", "warranty"];

function showError(message) {
  $("error").textContent = message;
  show("error");
}

async function api(path, payload) {
  const res = await fetch(path, {
    method: payload ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`);
  return body;
}

function row(text, cls) {
  $("outcomes").insertAdjacentHTML(
    "afterbegin", `<div class="row ${cls ?? ""}">${text}</div>`);
}

async function ask(key) {
  hide("error");
  try {
    const body = await api("/api/ask", { key, owner: "web-user" });
    lastTrace = body.trace_id;
    $("rate-btn").disabled = false;
    row(`<b>[${body.trace_id}]</b> ${body.answer}`);
  } catch (e) { showError(String(e.message ?? e)); }
}

async function rate() {
  if (!lastTrace) return;
  hide("error");
  try {
    const body = await api("/api/rate", {
      trace_id: lastTrace,
      rating: Number($("rating").value),
      owner: "web-user",
    });
    row(`captured rating for <b>${lastTrace}</b> (${body.item_id.slice(0, 8)}…)`, "muted");
    refreshStats();
  } catch (e) { showError(String(e.message ?? e)); }
}

async function refreshStats() {
  const s = await api("/api/stats/web-user");
  $("stats").textContent =
    `total=${s.total} · average=${s.average}` +
    (s.by_type.rating ? ` · ratings=${s.by_type.rating}` : "");
}

async function regress() {
  hide("error");
  try {
    const r = await api("/api/regress", { owner: "web-user" });
    row(`<b>run</b> ${r.run_id} — samples=${r.total_samples} ` +
        `passed=${r.passed_samples} avg=${r.average_score} ` +
        `failing=[${r.failing_ids.join(", ") || "none"}]`);
    $("runs-body").insertAdjacentHTML("afterbegin",
      `<tr><td>${r.run_id}</td><td>${r.passed_samples}/${r.total_samples}</td></tr>`);
  } catch (e) { showError(String(e.message ?? e)); }
}

KEYS.forEach((key) => {
  const b = document.createElement("button");
  b.textContent = key.replaceAll("-", " ");
  b.addEventListener("click", () => ask(key));
  $("questions").appendChild(b);
});
$("ask-form").addEventListener("submit", (e) => { e.preventDefault(); rate(); });
$("regress-btn").addEventListener("click", regress);
refreshStats();
