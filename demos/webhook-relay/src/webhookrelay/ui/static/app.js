/* Vanilla-JS client for the webhook relay console (no build step). */
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

async function refreshEvents() {
  try {
    const res = await fetch("/api/webhook/events");
    const data = await res.json();
    $("events-list").innerHTML = (data || []).map(function(e) {
      return '<div style="padding:.4rem 0;border-bottom:1px solid var(--border)">' +
        '<strong>' + (e.type || e.event) + '</strong> ' +
        '<span style="color:var(--ink-dim)">' + (e.timestamp || "") + '</span></div>';
    }).join("") || "<p>No events yet.</p>";
  } catch (_) { /* ignore */ }
}

$("btn-send").addEventListener("click", async function() {
  const eventType = $("event-type").value;
  const btn = $("btn-send");
  btn.disabled = true;
  try {
    const res = await fetch("/api/webhook/receive", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({event_type: eventType, payload: {id: Date.now()}, source: "console"})
    });
    const data = await res.json();
    log("sent webhook: " + eventType, "log-hit");
    await refreshEvents();
  } catch (e) { log("send failed: " + e.message, "log-error"); }
  finally { btn.disabled = false; }
});

refreshEvents();
setInterval(refreshEvents, 5000);
