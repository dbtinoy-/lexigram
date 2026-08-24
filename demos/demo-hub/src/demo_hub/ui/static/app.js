/* Vanilla-JS hub console (no build step). */
"use strict";
const $ = (id) => document.getElementById(id);
let filter = "all";

async function load() {
  const res = await fetch("/api/status");
  const { services } = await res.json();
  render(services);
}

function dot(s) {
  const cls = s.status === "up" ? "up" : s.status === "cli" ? "cli" : "down";
  return `<span class="dot ${cls}" title="${s.status}"></span>`;
}

function card(s) {
  const href = s.kind === "web"
    ? `${location.protocol}//${s.slug}.demos.lexigram.dev`
    : "https://docs.lexigram.dev";
  return `<a class="card ${filter !== "all" && !matchFilter(s) ? "hidden" : ""}"
    href="${href}" target="_blank" rel="noopener">
    ${dot(s)}<h3>${s.name}</h3><p>${s.blurb}</p>
    <code>:${s.port}</code><span class="lat">${s.latency_ms ?? ""}</span></a>`;
}

const CAPABILITY = new Set(["realtime-monitor","resilient-rates","event-driven-orders",
  "rag-docs","support-agent","memory-chat","ai-guardrails","prompt-lab","feedback-loop"]);
function matchFilter(s) {
  return filter === "capability" ? CAPABILITY.has(s.slug) : !CAPABILITY.has(s.slug);
}

function render(services) {
  $("cards").innerHTML = services.map(card).join("");
}
document.querySelectorAll("#filters button").forEach((b) =>
  b.addEventListener("click", () => { filter = b.dataset.f;
    document.querySelectorAll("#filters button").forEach((x) => x.classList.toggle("active", x === b));
    load(); }));
load();
setInterval(load, 5000);
