/* Vanilla-JS client for the queue worker console (no build step). */
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
    const topic = encodeURIComponent($("topic").value.trim() || "tasks");
    const [sizeResponse, processedResponse] = await Promise.all([
      fetch(`/api/queue/size?topic=${topic}`),
      fetch("/api/queue/processed"),
    ]);
    const size = await readResponse(sizeResponse);
    const processed = await readResponse(processedResponse);
    $("queue-stats").innerHTML =
      `<div class="queue-stat"><span>Topic</span><strong>${size.topic}</strong></div>` +
      `<div class="queue-stat"><span>Pending</span><strong>${size.size}</strong></div>` +
      `<div class="queue-stat"><span>Processed</span><strong>${processed.count}</strong></div>`;
  } catch (e) {
    log(`refresh failed: ${e.message}`, "log-error");
    showError(`Queue status unavailable: ${e.message}`);
  }
}

async function publish(event) {
  event.preventDefault();
  const topic = $("topic").value.trim();
  const payload = $("job-payload").value.trim();
  if (!topic || !payload) {
    showError("Enter a topic and payload first.");
    return;
  }

  const btn = $("btn-enqueue");
  btn.disabled = true;
  showError("");
  try {
    const res = await fetch("/api/queue/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, payload: { text: payload } }),
    });
    const data = await readResponse(res);
    log(`enqueued ${data.message_id.slice(0, 8)} on ${data.topic}`, "log-hit");
    $("job-payload").value = "";
    await refreshStats();
  } catch (e) {
    showError(e.message);
    log(`enqueue failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

async function process(topic, batch = false) {
  const btn = $(batch ? "process-batch" : "process-next");
  btn.disabled = true;
  showError("");
  try {
    const path = batch ? "/api/queue/process/batch" : "/api/queue/process";
    const body = batch ? { topic, batch_size: 10 } : { topic };
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await readResponse(res);
    const count = batch ? data.processed : data.message_id ? 1 : 0;
    log(count ? `processed ${count} message${count === 1 ? "" : "s"}` : "nothing to process", count ? "log-hit" : "");
    await refreshStats();
  } catch (e) {
    showError(e.message);
    log(`process failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

$("enqueue-form").addEventListener("submit", publish);
$("process-next").addEventListener("click", () => process($("topic").value.trim()));
$("process-batch").addEventListener("click", () => process($("topic").value.trim(), true));
refreshStats();
setInterval(refreshStats, 3000);
