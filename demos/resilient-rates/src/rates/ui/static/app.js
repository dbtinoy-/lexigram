/* Vanilla-JS client for the resilient rates desk (no build step). */
"use strict";

const PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY"];
let scenario = "healthy";

const $ = (id) => document.getElementById(id);
const show = (el) => el.classList.remove("hidden");
const hide = (el) => el.classList.add("hidden");

function ts() {
  return new Date().toLocaleTimeString();
}

function log(msg, cls) {
  const el = document.createElement("div");
  el.className = "log-entry " + (cls || "");
  el.innerHTML = '<span class="log-time">' + ts() + "</span>" + msg;
  const log = $("log");
  log.prepend(el);
  if (log.children.length > 50) log.lastChild.remove();
}

function sourceClass(source) {
  if (source === "upstream") return "source-upstream";
  if (source === "cache") return "source-cache";
  if (source === "stale") return "source-stale";
  return "";
}

function renderPair(pair, data) {
  const card = $("card-" + pair.replace("/", "-"));
  if (!data || data.error) {
    card.className = "pair-card error";
    card.querySelector(".pair-rate").textContent = "--";
    card.querySelector(".pair-source").textContent = "";
    card.querySelector(".pair-time").textContent = "";
    card.querySelector(".pair-error").textContent = data ? data.error : "";
    show(card.querySelector(".pair-error"));
    return;
  }
  card.className = "pair-card";
  hide(card.querySelector(".pair-error"));
  card.querySelector(".pair-rate").textContent = data.rate;
  const src = card.querySelector(".pair-source");
  src.textContent = data.source;
  src.className = "pair-source " + sourceClass(data.source);
  card.querySelector(".pair-time").textContent = new Date(data.fetched_at * 1000).toLocaleTimeString();
}

async function fetchPair(pair) {
  const card = $("card-" + pair.replace("/", "-"));
  const btn = card.querySelector("button");
  btn.disabled = true;
  btn.textContent = "...";
  try {
    const res = await fetch("/rates/" + encodeURIComponent(pair));
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      renderPair(pair, { error: body.detail || "HTTP " + res.status });
      log(pair + " &mdash; " + (body.detail || "error"), "log-error");
    } else {
      const data = await res.json();
      renderPair(pair, data);
      log(pair + " &mdash; " + data.rate + " (" + data.source + ")", "log-" + (data.source === "upstream" ? "miss" : data.source === "stale" ? "stale" : "hit"));
    }
  } catch (e) {
    renderPair(pair, { error: e.message });
    log(pair + " &mdash; " + e.message, "log-error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Fetch";
  }
}

async function fetchAll() {
  await Promise.all(PAIRS.map(fetchPair));
}

async function refreshStats() {
  try {
    const res = await fetch("/stats");
    const s = await res.json();
    $("s-hits").textContent = s.hits;
    $("s-misses").textContent = s.misses;
    $("s-upstream").textContent = s.upstream_calls;
    $("s-retries").textContent = s.retries;
    $("s-stale").textContent = s.stale_served;
  } catch (_) { /* ignore */ }
}

async function setScenario(name) {
  try {
    await fetch("/scenario/" + name, { method: "POST" });
    scenario = name;
    document.querySelectorAll("#scenarios button").forEach((b) => {
      b.classList.toggle("active", b.dataset.scenario === name);
    });
    log("scenario &rarr; " + name);
  } catch (e) {
    log("scenario change failed: " + e.message, "log-error");
  }
}

async function clearCache() {
  try {
    await fetch("/cache/clear", { method: "POST" });
    log("cache cleared");
    await fetchAll();
  } catch (e) {
    log("clear failed: " + e.message, "log-error");
  }
}

async function stampede() {
  const btn = $("btn-stampede");
  btn.disabled = true;
  btn.textContent = "Running...";
  try {
    const res = await fetch("/stampede/USD/JPY?workers=10", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      log("stampede: " + data.workers + " workers &rarr; " + data.distinct_rates + " distinct rate(s), " + data.upstream_calls + " upstream call(s)");
      await refreshStats();
    } else {
      log("stampede failed", "log-error");
    }
  } catch (e) {
    log("stampede failed: " + e.message, "log-error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Stampede (10 concurrent)";
  }
}

async function runDemo() {
  const btn = $("btn-demo");
  btn.disabled = true;
  btn.textContent = "Running demo...";
  log("=== 5-act demo started ===", "log-hit");
  try {
    const res = await fetch("/demo", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      log("=== demo complete (" + data.acts + " acts) ===", "log-hit");
    } else {
      log("demo stopped at act " + (data.act || "?") + ": " + (data.error || "unknown"), "log-error");
    }
    await refreshStats();
    await fetchAll();
  } catch (e) {
    log("demo failed: " + e.message, "log-error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Run 5-Act Demo";
  }
}

function buildCards() {
  const container = $("pair-cards");
  PAIRS.forEach((pair) => {
    const id = "card-" + pair.replace("/", "-");
    const div = document.createElement("div");
    div.id = id;
    div.className = "pair-card";
    div.innerHTML =
      '<div class="pair-name">' + pair + "</div>" +
      '<div class="pair-rate">--</div>' +
      '<div class="pair-source"></div>' +
      '<div class="pair-time"></div>' +
      '<div class="pair-error hidden"></div>' +
      '<button>Fetch</button>';
    div.querySelector("button").addEventListener("click", () => fetchPair(pair));
    container.appendChild(div);
  });
}

/* Wire up */
buildCards();

document.querySelectorAll("#scenarios button").forEach((b) =>
  b.addEventListener("click", () => setScenario(b.dataset.scenario))
);
$("clear-cache").addEventListener("click", clearCache);
$("btn-stampede").addEventListener("click", stampede);
$("btn-demo").addEventListener("click", runDemo);

/* Initial load */
fetchAll();
refreshStats();

/* Auto-refresh stats every 3s */
setInterval(refreshStats, 3000);
