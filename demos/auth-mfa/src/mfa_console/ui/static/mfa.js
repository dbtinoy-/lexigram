/* MFA console logic: identity, status, enroll, disable, logout. */

async function loadProfile() {
  const me = await api("/api/me");
  if (!me.ok) {
    window.location.href = "/login";
    return;
  }
  document.getElementById("identity").innerHTML =
    `<div class="row"><span>${me.body.name}</span>` +
    `<span class="muted">${me.body.email}</span></div>`;

  const status = await api("/api/mfa/status");
  if (!status.ok) return;

  const enabled = status.body.enabled;
  document.getElementById("mfa-state").textContent = enabled
    ? "enabled"
    : "disabled";
  document.getElementById("enroll-box").style.display = enabled ? "none" : "";
  document.getElementById("enrolled-box").style.display = enabled ? "" : "none";
  if (enabled) {
    document.getElementById("codes-left").textContent =
      status.body.backup_codes_left;
  }
}

document.getElementById("enroll-btn")?.addEventListener("click", async () => {
  showError("");
  const result = await api("/api/mfa/enroll", { method: "POST" });
  if (!result.ok) {
    showError(result.body.error || "Enrollment failed");
    return;
  }
  const out = document.getElementById("enroll-output");
  out.textContent =
    `SECRET: ${result.body.secret}\n` +
    `URI: ${result.body.provisioning_uri}\n` +
    `BACKUP CODES (shown once): ${result.body.backup_codes.join(", ")}`;
});

document.getElementById("disable-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const form = new FormData(event.target);
  const result = await api("/api/mfa/disable", {
    method: "POST",
    body: JSON.stringify({ password: form.get("password") }),
  });
  if (!result.ok) {
    showError(result.body.error || "Disable failed");
    return;
  }
  loadProfile();
});

document.getElementById("logout").addEventListener("click", async (event) => {
  event.preventDefault();
  await api("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

loadProfile();
