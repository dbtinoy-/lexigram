/* Vanilla-JS hub console (no build step). */
"use strict";
const $ = (id) => document.getElementById(id);
let filter = "all";

async function load() {
  const status = $("hub-status");
  try {
    const res = await fetch("/api/status", { cache: "no-store" });
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.error) throw new Error(body.error || `HTTP ${res.status}`);
    const services = body.services || [];
    render(services);
    status.textContent = `${services.length} demos · status refreshes automatically`;
    status.className = "hub-status";
  } catch (error) {
    status.textContent = `Unable to load demo status: ${error.message}`;
    status.className = "hub-status error";
    if (!$("cards").children.length) {
      $("cards").innerHTML = "<p class=\"modal-error\">Try refreshing the hub.</p>";
    }
  }
}

function dot(s) {
  const cls = s.status === "up" ? "up" : s.status === "cli" ? "cli" : "down";
  return `<span class="dot ${cls}" title="${s.status}"></span>`;
}

function card(s) {
  const err = s.error ? ` title="${s.error.replace(/"/g, "&quot;")}"` : "";
  const href = s.kind === "web"
    ? `/demos/${s.slug}/`
    : "https://docs.lexigram.dev";
  const port = s.kind === "web"
    ? `<code>standalone :${s.port}</code>`
    : `<code>cli / notebook</code>`;
  const infoBtn = s.kind === "web"
    ? `<button type="button" class="info-btn" data-slug="${s.slug}" data-name="${s.name.replace(/"/g, "&quot;")}" title="About this demo" aria-label="About ${s.name.replace(/"/g, "&quot;")}">&#9432;</button>`
    : "";
  return `<div class="card-wrap ${filter !== "all" && s.group !== filter ? "hidden" : ""}">
    <a class="card" href="${href}"${err}>
      ${dot(s)}<h3>${s.name}</h3><p>${s.blurb}</p>
      ${port}</a>
    ${infoBtn}</div>`;
}

function render(services) {
  /* Group cards by group, preserving registry order within each group. */
  const groups = {};
  for (const s of services) {
    const g = s.group || "standard";
    if (!groups[g]) groups[g] = [];
    groups[g].push(s);
  }

  const groupLabels = { "standard": "Standard", "multi-module": "Multi-module" };
  let html = "";
  for (const [key, items] of Object.entries(groups)) {
    if (filter !== "all" && key !== filter) continue;
    const label = groupLabels[key] || key;
    html += `<div class="group-section"><h2 class="group-title">${label}</h2>`;
    html += `<div class="grid">`;
    html += items.map(card).join("");
    html += `</div></div>`;
  }
  $("cards").innerHTML = html;
  document.querySelectorAll(".info-btn").forEach((btn) =>
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openModal(btn.dataset.slug, btn.dataset.name);
    }));
}

/* ── Modal ─────────────────────────────────────────────────────────── */
function openModal(slug, name) {
  $("modal-title").textContent = name;
  $("modal-body").innerHTML = `<p class="modal-loading">Loading...</p>`;
  $("modal-overlay").classList.remove("hidden");
  document.body.style.overflow = "hidden";

  fetch(`/api/demo/${slug}/readme`, { cache: "no-store" })
    .then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.error) throw new Error(data.error || `HTTP ${r.status}`);
      return data;
    })
    .then((data) => {
      $("modal-body").innerHTML = renderMarkdown(data.readme || "No README available.");
    })
    .catch(() => {
      $("modal-body").innerHTML = `<p class="modal-error">Failed to load README.</p>`;
    });
}

function closeModal() {
  $("modal-overlay").classList.add("hidden");
  document.body.style.overflow = "";
}

$("modal-close").addEventListener("click", closeModal);
$("modal-overlay").addEventListener("click", (e) => {
  if (e.target === $("modal-overlay")) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

/* ── Minimal Markdown → HTML (headers, tables, code blocks, lists, paragraphs) ── */
function renderMarkdown(md) {
  const lines = md.split("\n");
  let html = "";
  let inCode = false;
  let inTable = false;
  let inList = false;

  for (const line of lines) {
    /* fenced code blocks */
    if (line.startsWith("```")) {
      if (inCode) { html += "</code></pre>"; inCode = false; }
      else { html += `<pre><code>`; inCode = true; }
      continue;
    }
    if (inCode) { html += esc(line) + "\n"; continue; }

    /* tables */
    if (line.includes("|") && line.trim().startsWith("|")) {
      if (!inTable) { html += "<table>"; inTable = true; }
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      if (cells.every((c) => /^[-:]+$/.test(c))) continue; /* separator row */
      const tag = html.endsWith("<tr>") ? "td" : "td";
      html += "<tr>" + cells.map((c) => `<${tag}>${inlineMd(c)}</${tag}>`).join("") + "</tr>";
      continue;
    } else if (inTable) {
      html += "</table>"; inTable = false;
    }

    /* lists */
    if (/^\s*[-*]\s/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inlineMd(line.replace(/^\s*[-*]\s/, ""))}</li>`;
      continue;
    } else if (inList) {
      html += "</ul>"; inList = false;
    }

    /* blank line */
    if (!line.trim()) { html += "\n"; continue; }

    /* headers */
    const hMatch = line.match(/^(#{1,6})\s+(.*)/);
    if (hMatch) {
      const level = hMatch[1].length;
      html += `<h${level}>${inlineMd(hMatch[2])}</h${level}>`;
      continue;
    }

    /* paragraph text */
    html += `<p>${inlineMd(line)}</p>`;
  }
  if (inCode) html += "</code></pre>";
  if (inTable) html += "</table>";
  if (inList) html += "</ul>";
  return html;
}

function inlineMd(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
}

function esc(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

/* ── Filters ───────────────────────────────────────────────────────── */
document.querySelectorAll("#filters button").forEach((b) =>
  b.addEventListener("click", () => { filter = b.dataset.f;
    document.querySelectorAll("#filters button").forEach((x) => x.classList.toggle("active", x === b));
    load(); }));
load();
setInterval(load, 5000);
