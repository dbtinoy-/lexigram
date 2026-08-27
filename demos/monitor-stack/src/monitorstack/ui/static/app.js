/* Vanilla-JS client for the monitor stack console (no build step). */
"use strict";

const $ = (id) => document.getElementById(id);
function ts() { return new Date().toLocaleTimeString(); }
function log(msg, cls) {
  const el = document.createElement("div");
  el.className = "log-entry " + (cls || "");
  el.innerHTML = '<span class="log-time">' + ts() + "</span>" + msg;
  const logEl = $("log");
  logEl.prepend(el);
  if (logEl.children.length > 50) logEl.lastChild.remove();
}

async function refreshHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    $("health-grid").innerHTML =
      '<div style="display:flex;gap:1rem;">' +
      '<div>Status: <strong style="color:var(--ok)">' + (data.status || "ok") + '</strong></div>' +
      '<div>Checks: <strong>' + (data.checks ? data.checks.length : 0) + '</strong></div>' +
      '</div>';
    log("health check passed", "log-hit");
  } catch (e) { log("health check failed: " + e.message, "log-error"); }
}

async function refreshMetrics() {
  try {
    const res = await fetch("/api/metrics");
    const data = await res.json();
    $("metrics-grid").innerHTML =
      '<div style="display:flex;gap:1rem;">' +
      '<div>Requests: <strong>' + (data.requests || 0) + '</strong></div>' +
      '<div>Errors: <strong>' + (data.errors || 0) + '</strong></div>' +
      '<div>Uptime: <strong>' + (data.uptime || "0s") + '</strong></div>' +
      '</div>';
  } catch (_) { /* ignore */ }
}

refreshHealth(); refreshMetrics();
setInterval(refreshHealth, 5000);
setInterval(refreshMetrics, 3000);
