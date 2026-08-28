/* Vanilla-JS client for the feedback-loop console (no build step). */
"use strict";

let lastTrace = null;
const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");
const escapeHtml = (text) => {
  const element = document.createElement("div");
  element.textContent = String(text);
  return element.innerHTML;
};

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
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.error || body.detail) {
    throw new Error(body.error || body.detail || `HTTP ${res.status}`);
  }
  return body;
}

function row(text, cls) {
  const element = document.createElement("div");
  element.className = `row ${cls || ""}`;
  element.innerHTML = text;
  $("outcomes").prepend(element);
}

async function ask(key, button) {
  hide("error");
  button.disabled = true;
  try {
    const body = await api("/api/ask", { key, owner: "web-user" });
    lastTrace = body.trace_id;
    $("rate-btn").disabled = false;
    row(`<b>[${escapeHtml(body.trace_id)}]</b> ${escapeHtml(body.answer)}`);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
}

async function rate() {
  if (!lastTrace) return;
  hide("error");
  const rateButton = $("rate-btn");
  rateButton.disabled = true;
  try {
    const trace = lastTrace;
    const body = await api("/api/rate", {
      trace_id: trace,
      rating: Number($("rating").value),
      owner: "web-user",
    });
    row(`captured rating for <b>${escapeHtml(trace)}</b> (${escapeHtml(body.item_id.slice(0, 8))}…)`, "muted");
    await refreshStats();
    lastTrace = null;
  } catch (error) {
    rateButton.disabled = false;
    showError(error.message);
  }
}

async function refreshStats() {
  try {
    const s = await api("/api/stats/web-user");
    $("stats").textContent =
      `total=${s.total} · average=${s.average}` +
      (s.by_type.rating ? ` · ratings=${s.by_type.rating}` : "");
  } catch (error) {
    showError(`Stats unavailable: ${error.message}`);
  }
}

async function regress() {
  hide("error");
  const button = $("regress-btn");
  button.disabled = true;
  try {
    const r = await api("/api/regress", { owner: "web-user" });
    row(`<b>run</b> ${escapeHtml(r.run_id)} — samples=${r.total_samples} ` +
        `passed=${r.passed_samples} avg=${r.average_score} ` +
        `failing=[${escapeHtml(r.failing_ids.join(", ") || "none")}]`);
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(r.run_id)}</td><td>${r.passed_samples}/${r.total_samples}</td>`;
    $("runs-body").prepend(tr);
  } catch (error) {
    if (error.message.includes("no low-rated feedback")) {
      row("No low-rated feedback to regress yet — rate some answers 1-2 first.", "muted");
    } else {
      showError(error.message);
    }
  } finally {
    button.disabled = false;
  }
}

KEYS.forEach((key) => {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = key.replaceAll("-", " ");
  button.addEventListener("click", () => ask(key, button));
  $("questions").appendChild(button);
});
$("ask-form").addEventListener("submit", (event) => { event.preventDefault(); rate(); });
$("regress-btn").addEventListener("click", regress);
refreshStats();
