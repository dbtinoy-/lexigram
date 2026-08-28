/* Vanilla-JS client for the RAG pipeline console (no build step). */
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

async function search(event) {
  event.preventDefault();
  const query = $("query-input").value.trim();
  if (!query) {
    showError("Ask a question first.");
    $("query-input").focus();
    return;
  }
  const btn = $("btn-query");
  btn.disabled = true;
  showError("");
  try {
    const res = await fetch("/api/rag/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await readResponse(res);
    $("results").innerHTML = (data.results || []).map(function(result) {
      const score = Number(result.score || 0).toFixed(3);
      return `<article class="result"><strong>${score}</strong><p>${escapeHtml(result.content || "")}</p></article>`;
    }).join("") || "<p class=\"muted\">No results.</p>";
    log(`query returned ${(data.results || []).length} result(s)`, "log-hit");
  } catch (e) {
    showError(e.message);
    log(`query failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

async function ingest(event) {
  event.preventDefault();
  const content = $("doc-input").value.trim();
  if (!content) {
    showError("Paste document text first.");
    $("doc-input").focus();
    return;
  }
  const btn = $("btn-ingest");
  btn.disabled = true;
  showError("");
  try {
    const res = await fetch("/api/rag/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const data = await readResponse(res);
    log(`ingested document: ${data.chunks_stored} chunk(s)`, "log-hit");
    $("doc-input").value = "";
  } catch (e) {
    showError(e.message);
    log(`ingest failed: ${e.message}`, "log-error");
  } finally {
    btn.disabled = false;
  }
}

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = text;
  return element.innerHTML;
}

$("query-form").addEventListener("submit", search);
$("ingest-form").addEventListener("submit", ingest);
