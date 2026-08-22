/* Realtime monitor dashboard client.
 *
 * Consumes the SSE stream (replaying server-rendered history from #feed-data),
 * keeps a capped local feed, and renders rows with DOM APIs only — never
 * innerHTML — so event messages are displayed as text, not markup.
 */
"use strict";

const feed = [];
let paused = false;
let buffered = 0;
const MAX_ROWS = 300;

const tbody = document.getElementById("events");
const empty = document.getElementById("empty");
const search = document.getElementById("search");
const filterSev = document.getElementById("filter-sev");
const pauseBtn = document.getElementById("pause");
const clearBtn = document.getElementById("clear");
const subsEl = document.getElementById("subs");
const histEl = document.getElementById("hist");
const beatEl = document.getElementById("beat");
const dot = document.getElementById("conn-dot");
const connLabel = document.getElementById("conn-label");
const form = document.getElementById("publish-form");
const msgInput = document.getElementById("msg");
const srcInput = document.getElementById("src");
const sevInput = document.getElementById("sev");
const publishBtn = document.getElementById("publish-btn");

function td(cls) {
  const cell = document.createElement("td");
  cell.className = cls;
  return cell;
}

function buildRow(d) {
  const tr = document.createElement("tr");
  tr.className = "row b-" + (d.severity || "info");
  const t = td("time");
  t.textContent = (d.occurred_at || "").slice(11, 19);
  const b = td("sev");
  const badge = document.createElement("span");
  badge.className = "badge b-" + (d.severity || "info");
  badge.textContent = (d.severity || "info").toUpperCase();
  b.appendChild(badge);
  const s = td("src");
  s.textContent = (d.source || "") + " \u00b7 " + (d.kind || "");
  const m = td("msg");
  m.textContent = d.message || "";
  tr.append(t, b, s, m);
  return tr;
}

function matches(d) {
  const sev = filterSev.value;
  if (sev !== "all" && d.severity !== sev) return false;
  const q = search.value.trim().toLowerCase();
  if (!q) return true;
  return (
    d.message + " " + (d.source || "") + " " + (d.kind || "")
  ).toLowerCase().includes(q);
}

function render() {
  tbody.replaceChildren();
  let shown = 0;
  for (const d of feed) {
    if (!matches(d)) continue;
    tbody.appendChild(buildRow(d));
    shown++;
  }
  empty.style.display = shown === 0 ? "" : "none";
  empty.textContent =
    feed.length === 0
      ? "No events yet — publish one below."
      : "No events match the current filter.";
}

function setStatus(state, label) {
  dot.className = "dot " + state;
  connLabel.textContent = label;
}

async function refreshStats() {
  try {
    const r = await fetch("/api/stats", { cache: "no-store" });
    const s = await r.json();
    subsEl.textContent = s.subscribers;
    histEl.textContent = s.history;
  } catch (_) {
    /* the dashboard stays usable while the server is unreachable */
  }
}

const es = new EventSource("/api/events/stream");
es.onopen = () => setStatus("live", "Live");
es.onerror = () => setStatus("reconnect", "Reconnecting\u2026");

es.addEventListener("heartbeat", (e) => {
  try {
    beatEl.textContent = new Date(
      JSON.parse(e.data).occurred_at
    ).toLocaleTimeString();
  } catch (_) {
    /* ignore malformed heartbeats */
  }
});

es.onmessage = (e) => {
  if (paused) {
    buffered++;
    pauseBtn.textContent = "Resume (" + buffered + ")";
    return;
  }
  let d;
  try {
    d = JSON.parse(e.data);
  } catch (_) {
    return;
  }
  feed.unshift(d);
  if (feed.length > MAX_ROWS) feed.pop();
  tbody.prepend(buildRow(d));
  empty.style.display = "none";
};

search.addEventListener("input", () => {
  clearTimeout(search._t);
  search._t = setTimeout(render, 150);
});
filterSev.addEventListener("change", render);

pauseBtn.addEventListener("click", () => {
  paused = !paused;
  pauseBtn.textContent = paused ? "Resume" : "Pause";
  if (!paused) {
    render();
    buffered = 0;
  }
});

clearBtn.addEventListener("click", () => {
  feed.length = 0;
  buffered = 0;
  render();
});

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  publishBtn.disabled = true;
  try {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msgInput.value.trim(),
        severity: sevInput.value,
        source: srcInput.value.trim() || "console",
      }),
    });
    msgInput.value = "";
  } finally {
    publishBtn.disabled = false;
  }
});

const seed = document.getElementById("feed-data");
if (seed) {
  try {
    for (const d of JSON.parse(seed.textContent)) feed.push(d);
  } catch (_) {
    /* fall back to an empty feed */
  }
}
render();

setInterval(refreshStats, 5000);
refreshStats();