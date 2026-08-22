/* Vanilla-JS client for the rag-docs console (no build step). */
"use strict";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

async function loadStats() {
  const s = await (await fetch("/stats")).json();
  $("stats").textContent = JSON.stringify(s, null, 2);
}

async function ask(event) {
  event.preventDefault();
  hide("error");
  const res = await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: $("question").value,
      strategy: $("strategy").value,
    }),
  });
  if (!res.ok) {
    $("error").textContent = (await res.json()).error;
    show("error");
    return;
  }
  const body = await res.json();
  $("answer").textContent = body.answer;
  $("citations").innerHTML = body.citations
    .map((c) => `<li><code>${c}</code></li>`)
    .join("");
}

$("ask-form").addEventListener("submit", ask);
loadStats();
