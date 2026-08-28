/* Browser controls for the Lexigram QueueModule + MessageConsumer demo. */
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

async function refreshStats() {
  try {
    const [healthResponse, processedResponse] = await Promise.all([
      fetch("/api/queue/health"),
      fetch("/api/queue/processed"),
    ]);
    const health = await readResponse(healthResponse);
    const processed = await readResponse(processedResponse);
    $("queue-stats").innerHTML =
      `<div class="queue-stat"><span>Topic</span><strong>${health.topic}</strong></div>` +
      `<div class="queue-stat"><span>Worker</span><strong>${health.status}</strong></div>` +
      `<div class="queue-stat"><span>Handled</span><strong>${processed.count}</strong></div>`;
  } catch (e) {
    log(`refresh failed: ${e.message}`, "log-error");
    showError(`Worker status unavailable: ${e.message}`);
  }
}

async function publish(event) {
  event.preventDefault();
  const payload = $("job-payload").value.trim();
  if (!payload) {
    showError("Enter a task payload first.");
    return;
  }

  const btn = $("btn-enqueue");
  btn.disabled = true;
  showError("");
  try {
    const res = await fetch("/api/queue/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload: { text: payload } }),
    });
    const data = await readResponse(res);
    log(`published ${data.message_id.slice(0, 8)} to ${data.topic}; consumer notified`, "log-hit");
    $("job-payload").value = "";
    await refreshStats();
  } catch (e) {
    showError(e.message);
    log(`publish failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

$("enqueue-form").addEventListener("submit", publish);
$("refresh-status").addEventListener("click", refreshStats);
refreshStats();
setInterval(refreshStats, 3000);
