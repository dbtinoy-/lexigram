/* Vanilla-JS client for the RAG pipeline console (no build step). */
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

$("btn-query").addEventListener("click", async function() {
  const q = $("query-input").value;
  if (!q.trim()) return;
  const btn = $("btn-query");
  btn.disabled = true;
  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({query: q})
    });
    const data = await res.json();
    $("results").innerHTML = (data.results || []).map(function(r) {
      return '<div style="padding:.5rem;margin:.4rem 0;background:var(--surface2);border-radius:6px;">' +
        '<strong>' + (r.score || "") + '</strong> — ' + (r.text || r.content || JSON.stringify(r)) + '</div>';
    }).join("") || "<p>No results.</p>";
    log("query returned " + (data.results || []).length + " results", "log-hit");
  } catch (e) { log("query failed: " + e.message, "log-error"); }
  finally { btn.disabled = false; }
});

$("btn-ingest").addEventListener("click", async function() {
  const text = $("doc-input").value;
  if (!text.trim()) return;
  const btn = $("btn-ingest");
  btn.disabled = true;
  try {
    const res = await fetch("/api/ingest", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text})
    });
    const data = await res.json();
    log("ingested document: " + (data.chunks || "?") + " chunks", "log-hit");
    $("doc-input").value = "";
  } catch (e) { log("ingest failed: " + e.message, "log-error"); }
  finally { btn.disabled = false; }
});
