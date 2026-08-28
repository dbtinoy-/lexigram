/* Vanilla-JS client for the content generator console (no build step). */
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

async function generate(event) {
  event.preventDefault();
  const btn = $("btn-generate");
  btn.disabled = true;
  try {
    const res = await fetch("/api/content/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: "Lexigram framework",
        style: $("style-select").value,
      }),
    });
    const data = await readResponse(res);
    $("output").textContent = data.content;
    showError("");
    log(`generated ${data.style} content`, "log-hit");
  } catch (e) {
    showError(e.message);
    log(`generate failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

async function extract(event) {
  event.preventDefault();
  const text = $("extract-input").value.trim();
  if (!text) {
    showError("Add a product description first.");
    $("extract-input").focus();
    return;
  }
  const btn = $("btn-extract");
  btn.disabled = true;
  try {
    const res = await fetch("/api/content/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description: text }),
    });
    const data = await readResponse(res);
    $("extract-output").textContent = JSON.stringify(data.product, null, 2);
    showError("");
    log("extracted product info", "log-hit");
  } catch (e) {
    showError(e.message);
    log(`extract failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

$("generate-form").addEventListener("submit", generate);
$("extract-form").addEventListener("submit", extract);
