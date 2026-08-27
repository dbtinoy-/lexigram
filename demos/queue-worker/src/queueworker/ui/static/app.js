/* Vanilla-JS client for the queue worker console (no build step). */
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

async function refreshStats() {
  try {
    const res = await fetch("/api/queue/status");
    const data = await res.json();
    $("queue-stats").innerHTML =
      '<div style="display:flex;gap:1rem;">' +
      '<div>Pending: <strong>' + (data.pending || 0) + '</strong></div>' +
      '<div>Processing: <strong>' + (data.processing || 0) + '</strong></div>' +
      '<div>Completed: <strong>' + (data.completed || 0) + '</strong></div>' +
      '</div>';
  } catch (_) { /* ignore */ }
}

$("btn-enqueue").addEventListener("click", async function() {
  const payload = $("job-payload").value || "demo-job";
  const btn = $("btn-enqueue");
  btn.disabled = true;
  try {
    const res = await fetch("/api/queue/enqueue", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({payload: payload})
    });
    const data = await res.json();
    log("enqueued job: " + (data.job_id || payload), "log-hit");
    $("job-payload").value = "";
    await refreshStats();
  } catch (e) { log("enqueue failed: " + e.message, "log-error"); }
  finally { btn.disabled = false; }
});

refreshStats();
setInterval(refreshStats, 3000);
