/* Vanilla-JS client for the memory-chat console (no build step). */
"use strict";

let owner = "alice";
const history = { alice: [], bob: [] };

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

function setActiveOwner() {
  document.querySelectorAll("#owners button").forEach((button) => {
    button.classList.toggle("active", button.dataset.owner === owner);
  });
  renderThread();
}

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = String(text);
  return element.innerHTML;
}

function bubble(sender, text, cited) {
  const chips = (cited ?? [])
    .map((citation) => `<span class="chip">${escapeHtml(citation)}</span>`)
    .join("");
  return `<div class="bubble ${sender}"><p>${escapeHtml(text)}</p>${chips}</div>`;
}

function renderThread() {
  $("thread").innerHTML = history[owner]
    .map((turn) => bubble(turn.sender, turn.text, turn.cited))
    .join("");
}

function showError(message) {
  $("error").textContent = message;
  show("error");
}

async function loadFacts() {
  try {
    const res = await fetch(`/api/facts/${encodeURIComponent(owner)}`);
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
    $("facts").innerHTML = data.triples.length
      ? data.triples
          .map((triple) => `<li><code>${triple.map(escapeHtml).join(" · ")}</code></li>`)
          .join("")
      : "<li class='muted'>nothing yet</li>";
  } catch (e) {
    $("facts").innerHTML = "<li class='muted'>Facts unavailable — send a message to start.</li>";
  }
}

async function send(event) {
  event.preventDefault();
  const message = $("message").value.trim();
  if (!message) return;
  const sendButton = $("ask-form").querySelector("button[type=submit]");
  sendButton.disabled = true;
  hide("error");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner, text: message }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.error) throw new Error(body.error || `HTTP ${res.status}`);
    history[owner].push({ sender: "user", text: message });
    history[owner].push({ sender: "bot", text: body.reply, cited: body.cited });
    $("message").value = "";
    renderThread();
    await loadFacts();
  } catch (e) {
    showError(e.message);
  } finally {
    sendButton.disabled = false;
  }
}

async function runDemo() {
  const demoButton = $("demo-btn");
  demoButton.disabled = true;
  hide("error");
  try {
    const res = await fetch("/api/demo", { method: "POST" });
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.error) throw new Error(body.error || `HTTP ${res.status}`);
    history.alice = [];
    history.bob = [];
    body.transcript.forEach((turn) =>
      history[turn.owner].push({ sender: "bot", text: `${turn.owner}: ${turn.reply}` }));
    renderThread();
    await loadFacts();
    if (!body.isolation_ok) {
      history[owner].push({ sender: "bot", text: "Isolation check failed — owner data may overlap." });
      renderThread();
    }
  } catch (e) {
    showError(`Demo failed: ${e.message}`);
  } finally {
    demoButton.disabled = false;
  }
}

document.querySelectorAll("#owners button").forEach((button) =>
  button.addEventListener("click", () => {
    owner = button.dataset.owner;
    setActiveOwner();
    loadFacts();
  }));
$("ask-form").addEventListener("submit", send);
$("demo-btn").addEventListener("click", runDemo);
setActiveOwner();
loadFacts();
