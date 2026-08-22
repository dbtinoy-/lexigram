/* Vanilla-JS client for the guardrails playground (no build step). */
"use strict";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

function badge(kind) {
  const map = { pass: "ok", redacted: "redact", blocked: "block",
                denied_model: "block", denied_budget: "block" };
  return `<span class="badge ${map[kind] ?? "block"}">${kind}</span>`;
}

function escapeHtml(s) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;");
}

function renderOutcome(o) {
  const bits = [badge(o.kind)];
  if (o.reply) bits.push(`<code>${escapeHtml(o.reply)}</code>`);
  if (o.reason) bits.push(`<em>${o.reason}</em>`);
  if (o.remaining_budget !== null && o.remaining_budget !== undefined) {
    bits.push(`<span class="muted">$${o.remaining_budget.toFixed(2)} left</span>`);
  }
  $("outcomes").insertAdjacentHTML(
    "afterbegin", `<div class="row">${bits.join(" ")}</div>`);
}

async function refreshState() {
  const s = await (await fetch("/api/state")).json();
  $("policy-toggle").checked = s.policy_enabled;
  $("state").textContent =
    `spent $${s.spent.toFixed(2)} / $${s.monthly_budget.toFixed(2)} · remaining $${s.remaining.toFixed(2)}`;
}

async function refreshAudit() {
  const { rows } = await (await fetch("/api/audit")).json();
  $("audit-body").innerHTML = rows.slice(0, 12).map((r) =>
    `<tr><td>${r.event_type}</td><td>${r.status ?? ""}</td><td>${r.cost ?? ""}</td></tr>`).join("");
}

async function ask(payload) {
  hide("error");
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    $("error").textContent = (await res.json()).error;
    show("error");
    return;
  }
  renderOutcome((await res.json()).outcome);
  await Promise.all([refreshState(), refreshAudit()]);
}

document.querySelectorAll("#acts button").forEach((b) =>
  b.addEventListener("click", () => ask({ act: b.dataset.act })));

$("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  ask({ text: $("text").value, model: $("model").value });
});

$("policy-toggle").addEventListener("change", (e) =>
  fetch("/api/policy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: e.target.checked }),
  }).then(refreshState));

refreshState();
refreshAudit();
