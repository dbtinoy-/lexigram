"""Profile password form adopts the shared admin form contract."""

from __future__ import annotations

from lexigram.admin.lib.template.profile import render_profile_page


def test_profile_password_form_has_shared_contract_and_csrf() -> None:
    html = render_profile_page(
        name="Ada Lovelace",
        email="ada@example.com",
        roles=["admin"],
        user_id="user-1",
        mfa_enabled=True,
        csrf_token="csrf-value",
        password_url="/backoffice/profile/password",
    )

    assert 'action="/backoffice/profile/password"' in html
    assert 'data-admin-form="true"' in html
    assert "data-admin-form-status" in html
    assert "data-admin-form-actions" in html
    assert 'name="csrf_token" value="csrf-value"' in html
