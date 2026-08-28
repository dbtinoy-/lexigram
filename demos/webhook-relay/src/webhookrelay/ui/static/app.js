/* Vanilla-JS client for the webhook relay console (no build step). */
"use strict";

const $ = (id) => document.getElementById(id);

function ts() { return new Date().toLocaleTimeString(); }
function log(msg, cls) {
  const el = document.createElement("div");
  el.className = "log-entry " + (cls || "");
  el.textContent = `${ts()} ${msg}`;
  const logEl = $("log");
  logEl.prepend(el);
  if (logEl.children.length > 50) logEl.lastChild.remove();
}

function showError(message) {
  const error = $("error");
  error.textContent = message;
  error.classList.toggle("hidden", !message);
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

async function refreshEvents() {
  try {
    const res = await fetch("/api/webhook/events");
    const data = await readResponse(res);
    const events = data.events || [];
    $("events-list").innerHTML = events.map(function(event) {
      return `<article class="event-row"><strong>${escapeHtml(event.event_type || event.type || "event")}</strong>` +
        `<span>${escapeHtml(event.status || "")}</span>` +
        `<time>${escapeHtml(event.timestamp || "")}</time></article>`;
    }).join("") || "<p class=\"muted\">No events yet.</p>";
  } catch (e) {
    log(`refresh failed: ${e.message}`, "log-error");
    showError(`Events unavailable: ${e.message}`);
  }
}

async function send(event) {
  event.preventDefault();
  const eventType = $("event-type").value;
  const btn = $("btn-send");
  btn.disabled = true;
  showError("");
  try {
    const res = await fetch("/api/webhook/receive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType, payload: { id: Date.now() }, source: "console" }),
    });
    const data = await readResponse(res);
    log(`sent ${eventType} (${data.status})`, "log-hit");
    await refreshEvents();
  } catch (e) {
    showError(e.message);
    log(`send failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = text;
  return element.innerHTML;
}

$("send-form").addEventListener("submit", send);
refreshEvents();
setInterval(refreshEvents, 5000);
