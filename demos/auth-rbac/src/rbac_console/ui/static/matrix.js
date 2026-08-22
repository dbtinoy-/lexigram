/* Matrix page: grid, try-verdict form, articles list. */

async function loadMe() {
  const me = await api("/api/me");
  if (!me.ok) {
    window.location.href = "/login";
    return;
  }
  document.getElementById("who").textContent =
    `${me.body.email} — ${me.body.roles.join(", ")}`;
}

async function loadMatrix() {
  const matrix = await api("/api/matrix");
  if (!matrix.ok) return;
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  for (const check of matrix.body.checks) {
    const row = document.createElement("tr");
    row.innerHTML = `<td><code>${check}</code></td>`;
    for (const role of matrix.body.personas) {
      const granted = matrix.body.cells[role][check];
      row.innerHTML += `<td class="${granted ? "ok" : "error"}">${granted ? "✓" : "✗"}</td>`;
    }
    grid.appendChild(row);
  }
}

document.getElementById("try-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await api("/api/try", {
    method: "POST",
    body: JSON.stringify({
      role: document.getElementById("try-role").value,
      action: document.getElementById("try-action").value,
      resource: document.getElementById("try-resource").value,
    }),
  });
  document.getElementById("verdict").textContent = JSON.stringify(result.body);
});

async function loadArticles() {
  const listing = await api("/api/articles");
  if (!listing.ok) return;
  const list = document.getElementById("article-list");
  list.innerHTML = "";
  for (const article of listing.body.articles) {
    const item = document.createElement("li");
    item.innerHTML = `<strong>${article.title}</strong> <span class="muted">${article.id}</span>`;
    list.appendChild(item);
  }
}

document.getElementById("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const title = document.getElementById("new-title").value;
  const created = await api("/api/articles", {
    method: "POST",
    body: JSON.stringify({ title, body: `Body for ${title}` }),
  });
  if (!created.ok) {
    showError(created.body.error || "Create failed");
    return;
  }
  loadArticles();
});

document.getElementById("logout").addEventListener("click", async (event) => {
  event.preventDefault();
  await api("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

loadMe();
loadMatrix();
loadArticles();
