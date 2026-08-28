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
  const element = document.createElement("div");
  element.textContent = String(s);
  return element.innerHTML;
}

function renderOutcome(o) {
  const bits = [badge(o.kind)];
  if (o.reply) bits.push(`<code>${escapeHtml(o.reply)}</code>`);
  if (o.reason) bits.push(`<em>${escapeHtml(o.reason)}</em>`);
  if (o.remaining_budget !== null && o.remaining_budget !== undefined) {
    bits.push(`<span class="muted">$${Number(o.remaining_budget).toFixed(2)} left</span>`);
  }
  $("outcomes").insertAdjacentHTML(
    "afterbegin", `<div class="row">${bits.join(" ")}</div>`);
}

function showError(message) {
  $("error").textContent = message;
  show("error");
}

async function refreshState() {
  const res = await fetch("/api/state");
  const s = await res.json().catch(() => ({}));
  if (!res.ok || s.error || s.detail) throw new Error(s.error || s.detail || `HTTP ${res.status}`);
  $("policy-toggle").checked = s.policy_enabled;
  $("state").textContent =
    `spent $${s.spent.toFixed(2)} / $${s.monthly_budget.toFixed(2)} · remaining $${s.remaining.toFixed(2)}`;
}

async function refreshAudit() {
  const res = await fetch("/api/audit");
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.error || body.detail) throw new Error(body.error || body.detail || `HTTP ${res.status}`);
  const rows = body.rows || [];
  $("audit-body").innerHTML = rows.slice(0, 12).map((r) =>
    `<tr><td>${escapeHtml(r.event_type)}</td><td>${escapeHtml(r.status ?? "")}</td><td>${escapeHtml(r.cost ?? "")}</td></tr>`).join("");
}

async function ask(payload) {
  hide("error");
  const controls = [...document.querySelectorAll("#acts button, #ask-form button")];
  controls.forEach((button) => { button.disabled = true; });
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.error || body.detail) {
      throw new Error(body.error || body.detail || `HTTP ${res.status}`);
    }
    renderOutcome(body.outcome);
    await Promise.all([refreshState(), refreshAudit()]);
  } catch (error) {
    showError(error.message);
  } finally {
    controls.forEach((button) => { button.disabled = false; });
  }
}

document.querySelectorAll("#acts button").forEach((b) =>
  b.addEventListener("click", () => ask({ act: b.dataset.act })));

$("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  ask({ text: $("text").value.trim(), model: $("model").value });
});

$("policy-toggle").addEventListener("change", async (e) => {
  const enabled = e.target.checked;
  try {
    const res = await fetch("/api/policy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.error || body.detail) throw new Error(body.error || body.detail || `HTTP ${res.status}`);
    await refreshState();
  } catch (error) {
    e.target.checked = !enabled;
    showError(error.message);
  }
});

Promise.all([refreshState(), refreshAudit()]).catch(() => {
  $("state").textContent = "Services not configured — start the demo to see budget state.";
  $("audit-body").innerHTML = "<tr><td colspan='3' class='muted'>No audit data yet.</td></tr>";
});
