/* Vanilla-JS client for the rag-docs split-screen console. */
"use strict";

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

const MAX_HISTORY = 5;
const history = [];

/* ── Stats ──────────────────────────────────────────────────── */
async function loadStats() {
  try {
    const s = await (await fetch("/stats")).json();
    $("stat-files").textContent = s.files;
    $("stat-chunks").textContent = s.chunks;
  } catch (_) {
    $("stat-files").textContent = "?";
    $("stat-chunks").textContent = "?";
  }
}

/* ── History ────────────────────────────────────────────────── */
function addHistory(question, strategy) {
  history.unshift({ question, strategy });
  if (history.length > MAX_HISTORY) history.pop();
  renderHistory();
}

function renderHistory() {
  const list = $("history");
  list.innerHTML = history
    .map(
      (h) =>
        `<li data-q="${escapeHtml(h.question).replace(/"/g, "&quot;")}" data-s="${escapeHtml(h.strategy)}">` +
        `<span class="strategy-tag">${escapeHtml(h.strategy)}</span>${escapeHtml(h.question)}</li>`
    )
    .join("");
  list.querySelectorAll("li").forEach((li) => {
    li.addEventListener("click", () => {
      $("question").value = li.dataset.q;
      $("strategy").value = li.dataset.s;
      $("question").focus();
    });
  });
}

/* ── Ask ────────────────────────────────────────────────────── */
async function ask(event) {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) return;

  const strategy = $("strategy").value;
  const askBtn = $("ask-btn");
  const demoBtn = $("demo-btn");

  askBtn.disabled = true;
  demoBtn.disabled = true;
  hide("error-toast");
  $("answer-area").classList.remove("empty-state");
  $("answer-area").innerHTML = '<p class="placeholder">Searching…</p>';
  hide("citations-area");

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, strategy }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      $("error-toast").textContent = err.detail || "Request failed";
      show("error-toast");
      $("answer-area").innerHTML = '<p class="placeholder">Ask a question to get started</p>';
      $("answer-area").classList.add("empty-state");
      return;
    }

    const body = await res.json();
    $("answer-area").innerHTML = `<p class="answer-text">${escapeHtml(body.answer)}</p>`;

    if (body.citations && body.citations.length > 0) {
      $("citations").innerHTML = body.citations
        .map((c) => `<li>${escapeHtml(c)}</li>`)
        .join("");
      show("citations-area");
    } else {
      hide("citations-area");
    }

    addHistory(question, strategy);
    loadStats();
  } catch (err) {
    $("error-toast").textContent = "Network error — is the server running?";
    show("error-toast");
    $("answer-area").innerHTML = '<p class="placeholder">Ask a question to get started</p>';
    $("answer-area").classList.add("empty-state");
  } finally {
    askBtn.disabled = false;
    demoBtn.disabled = false;
  }
}

/* ── Demo ───────────────────────────────────────────────────── */
const DEMO_QUESTIONS = [
  { q: "how do modules export services?", s: "vector" },
  { q: "what do providers register?", s: "mmr" },
  { q: "how does the outbox pattern work?", s: "vector" },
];

async function runDemo() {
  const askBtn = $("ask-btn");
  const demoBtn = $("demo-btn");
  const status = $("demo-status");
  askBtn.disabled = true;
  demoBtn.disabled = true;
  hide("error-toast");
  status.textContent = `Running question 1 of ${DEMO_QUESTIONS.length}…`;

  try {
    for (let index = 0; index < DEMO_QUESTIONS.length; index++) {
      const { q, s } = DEMO_QUESTIONS[index];
      $("question").value = q;
      $("strategy").value = s;
      status.textContent = `Running question ${index + 1} of ${DEMO_QUESTIONS.length}…`;
      $("answer-area").classList.remove("empty-state");
      $("answer-area").innerHTML = `<p class="placeholder">Searching: ${escapeHtml(q)}…</p>`;

      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, strategy: s }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || body.error || `HTTP ${res.status}`);
      }

      $("answer-area").innerHTML = `<p class="answer-text">${escapeHtml(body.answer)}</p>`;
      if (body.citations && body.citations.length > 0) {
        $("citations").innerHTML = body.citations
          .map((c) => `<li>${escapeHtml(c)}</li>`)
          .join("");
        show("citations-area");
      } else {
        hide("citations-area");
      }
      addHistory(q, s);
      status.textContent = `Completed question ${index + 1} of ${DEMO_QUESTIONS.length}`;

      /* brief pause between questions */
      if (index < DEMO_QUESTIONS.length - 1) {
        await new Promise((r) => setTimeout(r, 400));
      }
    }
    status.textContent = "Guided demo complete";
  } catch (error) {
    status.textContent = `Demo failed: ${error.message}`;
    $("error-toast").textContent = `Guided demo failed: ${error.message}`;
    show("error-toast");
  } finally {
    askBtn.disabled = false;
    demoBtn.disabled = false;
    loadStats();
  }
}

/* ── Helpers ────────────────────────────────────────────────── */
function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

/* ── Init ───────────────────────────────────────────────────── */
$("ask-form").addEventListener("submit", ask);
$("demo-btn").addEventListener("click", runDemo);
loadStats();
