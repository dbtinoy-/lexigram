"""Tests for canonical login-redirect URL construction."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from lexigram.admin.auth.next_url import build_login_redirect, encode_next_value


class TestEncodeNextValue:
    """Path encoding keeps redirects human-readable."""

    def test_path_separators_are_not_escaped(self) -> None:
        assert encode_next_value("/admin/profile/mfa") == "/admin/profile/mfa"

    def test_query_delimiters_are_escaped(self) -> None:
        encoded = encode_next_value("/admin/x?evil=1&next=/attacker")

        assert "%3F" in encoded
        assert "%26" in encoded
        assert "?evil=1&next=" not in encoded


class TestBuildLoginRedirect:
    """Redirect assembly is stable, readable, and injection-safe."""

    def test_bare_url_when_no_parameters(self) -> None:
        assert build_login_redirect("/admin/login") == "/admin/login"

    def test_next_path_is_readable(self) -> None:
        result = build_login_redirect("/admin/login", next_path="/admin/profile/mfa")

        assert result == "/admin/login?next=/admin/profile/mfa"

    def test_error_precedes_next(self) -> None:
        result = build_login_redirect(
            "/admin/login", next_path="/admin/profile", error="Session expired"
        )

        assert result.index("error=") < result.index("next=")

    def test_empty_values_are_omitted(self) -> None:
        assert build_login_redirect("/admin/login", next_path="", error="") == (
            "/admin/login"
        )

    def test_injected_parameters_stay_inside_next(self) -> None:
        result = build_login_redirect(
            "/admin/login", next_path="/admin/x?evil=1&next=/attacker"
        )

        params = parse_qs(urlparse(result).query)

        assert list(params) == ["next"]
        assert params["next"] == ["/admin/x?evil=1&next=/attacker"]

    def test_round_trips_through_query_parsing(self) -> None:
        path = "/admin/profile/mfa"

        result = build_login_redirect("/admin/login", next_path=path)
        params = parse_qs(urlparse(result).query)

        assert params["next"] == [path]
