/* Vanilla-JS client for the content generator console (no build step). */
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

$("btn-generate").addEventListener("click", async function() {
  const style = $("style-select").value;
  const btn = $("btn-generate");
  btn.disabled = true;
  try {
    const res = await fetch("/api/content/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({topic: "Lexigram framework", style: style})
    });
    const data = await res.json();
    $("output").textContent = data.content || data.error || JSON.stringify(data);
    log("generated " + style + " content", "log-hit");
  } catch (e) { log("generate failed: " + e.message, "log-error"); }
  finally { btn.disabled = false; }
});

$("btn-extract").addEventListener("click", async function() {
  const text = $("extract-input").value;
  if (!text.trim()) return;
  const btn = $("btn-extract");
  btn.disabled = true;
  try {
    const res = await fetch("/api/content/extract", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text})
    });
    const data = await res.json();
    $("extract-output").textContent = JSON.stringify(data, null, 2);
    log("extracted product info", "log-hit");
  } catch (e) { log("extract failed: " + e.message, "log-error"); }
  finally { btn.disabled = false; }
});
