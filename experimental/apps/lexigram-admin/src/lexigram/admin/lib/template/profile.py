"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from markupsafe import escape


def render_profile_page(
    *,
    name: str,
    email: str,
    roles: list[str],
    user_id: str,
    mfa_enabled: bool,
    csrf_token: str,
    current_password_err: str = "",
    new_password_err: str = "",
    confirmation_err: str = "",
    mfa_url: str = "/admin/profile/mfa",
    password_url: str = "/admin/profile/password",  # noqa: S107
) -> str:
    """Render the user profile page content for the admin shell.

    Displays account details, two-factor authentication status, and a
    change-password form.  MFA management (setup/disable) lives on the
    dedicated ``/admin/profile/mfa`` screen; this page links to it.

    Args:
        name: Display name of the current user.
        email: Email of the current user.
        roles: Roles assigned to the current user.
        user_id: Identifier of the current user.
        mfa_enabled: Whether two-factor authentication is active.
        csrf_token: CSRF token for the change-password form.
        current_password_err: Optional per-field error under the current-password input.
        new_password_err: Optional per-field error under the new-password input.
        confirmation_err: Optional per-field error under the confirm input.
        mfa_url: Mounted route for managing two-factor authentication.
        password_url: Mounted form action for changing the password.

    Returns:
        HTML string fragment for the profile page body.
    """

    def field_error(message: str) -> str:
        return (
            f'<p class="mt-1 text-xs text-destructive" role="alert">{escape(message)}</p>'
            if message
            else ""
        )

    error_ring = "border-destructive focus:ring-destructive"
    current_classes = f"mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {error_ring if current_password_err else ''}"
    new_classes = f"mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {error_ring if new_password_err else ''}"
    confirm_classes = f"mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {error_ring if confirmation_err else ''}"
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
    role_chips = "".join(
        f'<span class="inline-flex items-center rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium text-accent-foreground">{escape(role)}</span>'
        for role in roles
    )
    mfa_badge = (
        '<span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">Enabled</span>'
        if mfa_enabled
        else '<span class="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">Disabled</span>'
    )
    return f"""
    <div class="max-w-3xl mx-auto space-y-6">
      <div class="rounded-lg border border-border bg-card shadow-sm">
        <div class="flex items-center gap-4 p-6">
          <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">{escape(initials)}</div>
          <div class="min-w-0">
            <h2 class="text-xl font-bold text-foreground">{escape(name)}</h2>
            <p class="text-sm text-muted-foreground">{escape(email)}</p>
            <div class="mt-2 flex flex-wrap gap-1.5">{role_chips or '<span class="text-xs text-muted-foreground">No roles</span>'}</div>
          </div>
        </div>
        <div class="border-t border-border px-6 py-3 text-xs text-muted-foreground">User ID: <code>{escape(user_id)}</code></div>
      </div>

      <div class="rounded-lg border border-border bg-card shadow-sm">
        <div class="border-b border-border px-6 py-4">
          <h3 class="text-lg font-semibold text-foreground">Security</h3>
        </div>
        <div class="px-6 py-4 space-y-6">
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="font-medium text-foreground">Two-factor authentication</p>
              <p class="text-sm text-muted-foreground">Add an extra layer of security to your account.</p>
            </div>
            <div class="flex items-center gap-3">
              {mfa_badge}
              <a href="{escape(mfa_url)}"
                 class="inline-flex items-center rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium text-foreground shadow-sm hover:bg-accent">Manage</a>
            </div>
          </div>
          <hr class="border-border" />
          <form method="post" action="{escape(password_url)}" class="space-y-4" data-admin-form="true" aria-busy="false">
            <p data-admin-form-status aria-live="polite" class="sr-only"></p>
            <input type="hidden" name="csrf_token" value="{escape(csrf_token)}" />
            <div>
              <label for="current_password" class="block text-sm font-medium text-foreground">Current password</label>
              <input type="password" name="current_password" id="current_password" required
                     class="{current_classes}" />
              {field_error(current_password_err)}
            </div>
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label for="new_password" class="block text-sm font-medium text-foreground">New password</label>
                <input type="password" name="new_password" id="new_password" required minlength="8"
                       class="{new_classes}" />
                {field_error(new_password_err)}
              </div>
              <div>
                <label for="new_password_confirmation" class="block text-sm font-medium text-foreground">Confirm new password</label>
                <input type="password" name="new_password_confirmation" id="new_password_confirmation" required minlength="8"
                       class="{confirm_classes}" />
                {field_error(confirmation_err)}
              </div>
            </div>
            <div data-admin-form-actions class="flex justify-end border-t border-border pt-4">
              <button type="submit"
                      class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Change password</button>
            </div>
          </form>
        </div>
      </div>
    </div>
    """
