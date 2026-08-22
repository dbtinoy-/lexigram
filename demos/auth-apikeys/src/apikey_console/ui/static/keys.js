/* Keys page: list, create, revoke. */

async function loadKeys() {
  const listing = await api("/api/keys");
  if (listing.status === 401) {
    window.location.href = "/login";
    return;
  }
  const rows = document.getElementById("key-rows");
  rows.innerHTML = "";
  for (const key of listing.body.keys) {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${key.name}</td><td><code>${key.prefix}…</code></td>` +
      `<td>${key.scopes.join(", ") || "—"}</td>` +
      `<td class="muted">${key.expires_at ?? "never"}</td>` +
      `<td><button class="secondary" data-key="${key.key_id}">Revoke</button></td>`;
    rows.appendChild(tr);
  }
  for (const button of document.querySelectorAll("button[data-key]")) {
    button.addEventListener("click", async () => {
      await api(`/api/keys/${button.dataset.key}/revoke`, { method: "POST" });
      loadKeys();
    });
  }
}

document.getElementById("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const scopes = [];
  if (form.get("scope-read")) scopes.push("read");
  if (form.get("scope-write")) scopes.push("write");
  const created = await api("/api/keys/create", {
    method: "POST",
    body: JSON.stringify({ name: form.get("name"), scopes }),
  });
  const box = document.getElementById("raw-key-box");
  box.style.display = "";
  document.getElementById("raw-key").textContent = created.body.raw_key || "(failed)";
  loadKeys();
});

document.getElementById("logout").addEventListener("click", async (event) => {
  event.preventDefault();
  await api("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

loadKeys();
