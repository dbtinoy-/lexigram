/* Vanilla-JS client for the memory-chat console (no build step). */
"use strict";

let owner = "alice";
const history = { alice: [], bob: [] };

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

function setActiveOwner() {
  document.querySelectorAll("#owners button").forEach((b) => {
    b.classList.toggle("active", b.dataset.owner === owner);
  });
  renderThread();
}

function bubble(sender, text, cited) {
  const chips = (cited ?? [])
    .map((c) => `<span class="chip">${c}</span>`)
    .join("");
  return `<div class="bubble ${sender}"><p>${text}</p>${chips}</div>`;
}

function renderThread() {
  $("thread").innerHTML = history[owner]
    .map((t) => bubble(t.sender, t.text, t.cited))
    .join("");
}

async function loadFacts() {
  const res = await fetch(`/api/facts/${owner}`);
  const data = await res.json();
  $("facts").innerHTML = data.triples.length
    ? data.triples
        .map((t) => `<li><code>${t[0]}·${t[1]}·${t[2]}</code></li>`)
        .join("")
    : "<li class='muted'>nothing yet</li>";
}

function showError(message) {
  $("error").textContent = message;
  show("error");
}

async function send(event) {
  event.preventDefault();
  hide("error");
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ owner, text: $("message").value }),
  });
  if (!res.ok) return showError((await res.json()).error);
  const body = await res.json();
  history[owner].push({ sender: "user", text: $("message").value });
  history[owner].push({ sender: "bot", text: body.reply, cited: body.cited });
  $("message").value = "";
  renderThread();
  loadFacts();
}

async function runDemo() {
  hide("error");
  const body = await (await fetch("/api/demo", { method: "POST" })).json();
  history.alice = [];
  history.bob = [];
  body.transcript.forEach((t) =>
    history[t.owner].push({ sender: "bot", text: `${t.owner}: ${t.reply}` }));
  renderThread();
  loadFacts();
  if (!body.isolation_ok) showError("isolation violated!");
}

document.querySelectorAll("#owners button").forEach((b) =>
  b.addEventListener("click", () => {
    owner = b.dataset.owner;
    setActiveOwner();
    loadFacts();
  }));
$("ask-form").addEventListener("submit", send);
$("demo-btn").addEventListener("click", runDemo);
setActiveOwner();
loadFacts();
