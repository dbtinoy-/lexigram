"use strict";
const $ = (id) => document.getElementById(id);
const names = ["new_checkout", "search_experiment", "ai_assistant"];
function esc(value) { const el = document.createElement("span"); el.textContent = String(value ?? ""); return el.innerHTML; }
async function read(response) { const data = await response.json().catch(() => ({})); if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`); return data; }
function context() { return { user_id: $("user-id").value.trim() || "demo-user-42", plan: $("plan").value }; }
async function loadFlags() {
  try {
    const data = await read(await fetch(`/api/flags?user_id=${encodeURIComponent(context().user_id)}&plan=${encodeURIComponent(context().plan)}`, { cache: "no-store" }));
    $("cache-label").textContent = `TTL ${data.cache_ttl_seconds}s`;
    $("flags").innerHTML = data.flags.map((flag) => {
      const state = flag.enabled ? "enabled" : "off";
      const value = flag.variant ? `variant · ${flag.variant}` : `value · ${flag.value}`;
      const override = flag.override === null ? "provider" : `forced ${flag.override ? "on" : "off"}`;
      return `<article class="flag-row"><div><strong>${esc(flag.name)}</strong><small>${esc(flag.description)} · ${esc(flag.reason)}</small></div><div class="flag-meta"><span class="status ${state}">${state}</span><span>${esc(value)}</span><span class="override">${esc(override)}</span></div></article>`;
    }).join("");
  } catch (error) { $("flags").innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
async function evaluate(event) {
  event.preventDefault();
  try { const data = await read(await fetch("/api/flags/evaluate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "search_experiment", ...context() }) })); $("context-result").textContent = `${data.name}: ${data.variant || data.enabled} · ${data.reason} for ${data.context.user_id}`; await loadFlags(); } catch (error) { $("context-result").textContent = error.message; }
}
async function override(event) {
  event.preventDefault();
  const button = event.submitter;
  if (!button?.dataset.enabled) return;
  try { const data = await read(await fetch("/api/flags/override", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: $("override-name").value, enabled: button.dataset.enabled === "true", actor: $("actor").value }) })); $("override-result").textContent = data.message; await Promise.all([loadFlags(), loadAudit()]); } catch (error) { $("override-result").textContent = error.message; }
}
async function clearOverride() {
  try { const data = await read(await fetch("/api/flags/override/clear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: $("override-name").value }) })); $("override-result").textContent = data.message; await Promise.all([loadFlags(), loadAudit()]); } catch (error) { $("override-result").textContent = error.message; }
}
async function clearCache() {
  try { const data = await read(await fetch("/api/flags/cache/clear", { method: "POST" })); $("context-result").textContent = data.message; await loadFlags(); } catch (error) { $("context-result").textContent = error.message; }
}
async function loadAudit() {
  try { const data = await read(await fetch("/api/flags/audit", { cache: "no-store" })); $("audit").innerHTML = data.entries.length ? data.entries.map((entry) => `<div class="audit-row"><strong>${esc(entry.flag_name)}</strong><span>${entry.old_value === null ? "none" : entry.old_value} → ${entry.new_value}</span><span>${esc(entry.actor || "unknown")}</span><time>${esc(entry.timestamp)}</time></div>`).join("") : `<p class="muted">No runtime overrides yet. Try forcing a flag on or off.</p>`; } catch (error) { $("audit").innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
$("context-form").addEventListener("submit", evaluate);
$("override-form").addEventListener("submit", override);
$("clear-override").addEventListener("click", clearOverride);
$("clear-cache").addEventListener("click", clearCache);
$("refresh-audit").addEventListener("click", loadAudit);
loadFlags(); loadAudit();
setInterval(loadFlags, 8000);
