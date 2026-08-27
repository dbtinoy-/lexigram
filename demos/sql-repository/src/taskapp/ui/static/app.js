/* Vanilla-JS client for the task manager console (no build step). */
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

async function loadUsers() {
  try {
    const res = await fetch("/api/tasks/users");
    const data = await res.json();
    $("users-list").innerHTML = data.map(function(u) {
      return '<div style="padding:.4rem 0;border-bottom:1px solid var(--border)">' + u.name + ' &lt;' + u.email + '&gt; <span style="color:var(--ink-dim)">(' + u.role + ')</span></div>';
    }).join("");
    log("loaded " + data.length + " users", "log-hit");
  } catch (e) { log("load users failed: " + e.message, "log-error"); }
}

async function loadProjects() {
  try {
    const res = await fetch("/api/tasks/projects");
    const data = await res.json();
    $("projects-list").innerHTML = data.map(function(p) {
      return '<div style="padding:.4rem 0;border-bottom:1px solid var(--border)">' + p.name + ' <span style="color:var(--ink-dim)">(' + p.status + ')</span></div>';
    }).join("");
    log("loaded " + data.length + " projects", "log-hit");
  } catch (e) { log("load projects failed: " + e.message, "log-error"); }
}

async function loadTasks() {
  try {
    const res = await fetch("/api/tasks/tasks");
    const data = await res.json();
    $("tasks-list").innerHTML = data.map(function(t) {
      return '<div style="padding:.4rem 0;border-bottom:1px solid var(--border)">' + t.title + ' <span style="color:var(--ink-dim)">(' + t.status + ')</span></div>';
    }).join("");
    log("loaded " + data.length + " tasks", "log-hit");
  } catch (e) { log("load tasks failed: " + e.message, "log-error"); }
}

loadUsers(); loadProjects(); loadTasks();
