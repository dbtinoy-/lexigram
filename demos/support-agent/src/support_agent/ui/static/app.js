/* Vanilla-JS client for the support-agent console (no build step). */
"use strict";

let scenario = "happy";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

function setActiveButton() {
  document.querySelectorAll("#scenarios button").forEach((b) => {
    b.classList.toggle("active", b.dataset.scenario === scenario);
  });
}

async function loadTools() {
  const res = await fetch("/api/tools");
  const tools = await res.json();
  $("tools").innerHTML = tools
    .map((t) => `<li title="${t.description}"><code>${t.name}</code></li>`)
    .join("");
}

function row(step, call) {
  const outcome = call
    ? `${call.tool_name} ${call.succeeded ? "ok" : `FAILED: ${call.error ?? ""}`}`
    : "";
  return `<tr><td>${step.step_number}</td><td>${step.thought ?? ""}</td>` +
         `<td>${step.action ?? ""}</td><td>${outcome}</td></tr>`;
}

function render(body) {
  $("answer").textContent = body.answer;
  $("trace").querySelector("tbody").innerHTML =
    body.steps.map((s, i) => row(s, body.tool_calls[i])).join("");
  $("meta").textContent = `tokens=${body.total_tokens} · ${body.duration_ms} ms`;
  ["answer", "trace", "meta"].forEach(show);
}

async function ask(event) {
  event.preventDefault();
  ["answer", "trace", "meta", "error"].forEach(hide);
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: $("question").value, scenario }),
  });
  if (!res.ok) {
    const err = await res.json();
    $("error").textContent = err.error ?? `HTTP ${res.status}`;
    show("error");
    return;
  }
  render(await res.json());
}

document.querySelectorAll("#scenarios button").forEach((b) =>
  b.addEventListener("click", () => {
    scenario = b.dataset.scenario;
    setActiveButton();
  }));
$("ask-form").addEventListener("submit", ask);
setActiveButton();
loadTools();
