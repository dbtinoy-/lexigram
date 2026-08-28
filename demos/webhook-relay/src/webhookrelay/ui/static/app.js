/* Browser controls for Lexigram WebhookModule's subscription and verification path. */
"use strict";

const $ = (id) => document.getElementById(id);
let activeSubscription = null;

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

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = String(text);
  return element.innerHTML;
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error || data.valid === false) {
    throw new Error(data.error || "Signature rejected");
  }
  return data;
}

async function refreshSubscriptions() {
  try {
    const data = await readResponse(await fetch("/api/webhook/subscriptions"));
    const subscriptions = data.subscriptions || [];
    $("subscription-list").textContent =
      `${data.count} active subscription${data.count === 1 ? "" : "s"} managed by Lexigram`;
    if (!activeSubscription && subscriptions.length) {
      log("Lexigram has an active subscription; create one here to use its secret", "log-hit");
    }
  } catch (e) {
    log(`subscription refresh failed: ${e.message}`, "log-error");
  }
}

async function createSubscription(event) {
  event.preventDefault();
  const url = $("subscription-url").value.trim();
  const eventTypes = $("subscription-events").value
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const btn = $("btn-subscribe");
  btn.disabled = true;
  showError("");
  try {
    const response = await fetch("/api/webhook/subscriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, event_types: eventTypes }),
    });
    activeSubscription = await readResponse(response);
    $("subscription-output").innerHTML =
      `<strong>${escapeHtml(activeSubscription.subscription_id.slice(0, 8))}</strong>` +
      ` · secret generated · ${escapeHtml(activeSubscription.url)}`;
    log("created a Lexigram subscription; signing is ready", "log-hit");
    await refreshSubscriptions();
  } catch (e) {
    showError(e.message);
    log(`subscription failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

async function signPayload(payload, secret) {
  if (!window.crypto || !window.crypto.subtle) {
    throw new Error("Web Crypto is unavailable; use an HTTPS browser context");
  }
  const raw = JSON.stringify(payload, Object.keys(payload).sort());
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(raw)
  );
  return "sha256=" + Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function send(event) {
  event.preventDefault();
  const eventType = $("event-type").value;
  const signed = $("use-signature").checked;
  const payload = { id: Date.now() };
  const btn = $("btn-send");
  btn.disabled = true;
  showError("");
  try {
    const body = { event_type: eventType, payload, source: "console" };
    if (signed) {
      if (!activeSubscription) {
        throw new Error("Create a Lexigram subscription before signing an event");
      }
      body.subscription_id = activeSubscription.subscription_id;
      body.signature = await signPayload(payload, activeSubscription.secret);
    }
    const response = await fetch("/api/webhook/receive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await readResponse(response);
    log(`accepted ${eventType} (${data.verified ? "HMAC verified" : "demo mode"})`, "log-hit");
    await refreshEvents();
  } catch (e) {
    showError(e.message);
    log(`send failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

async function refreshEvents() {
  try {
    const data = await readResponse(await fetch("/api/webhook/events"));
    const events = data.events || [];
    $("events-list").innerHTML = events.map(function(item) {
      return `<article class="event-row"><strong>${escapeHtml(item.event_type || "event")}</strong>` +
        `<span>${escapeHtml(item.status || "")}</span>` +
        `<time>${escapeHtml(item.timestamp || "")}</time></article>`;
    }).join("") || "<p class=\"muted\">No events yet.</p>";
  } catch (e) {
    log(`event refresh failed: ${e.message}`, "log-error");
    showError(`Events unavailable: ${e.message}`);
  }
}

$("subscription-form").addEventListener("submit", createSubscription);
$("send-form").addEventListener("submit", send);
refreshSubscriptions();
refreshEvents();
setInterval(refreshSubscriptions, 10000);
setInterval(refreshEvents, 5000);
