from __future__ import annotations

from pathlib import Path

from dev._lib.rule_engine import run_rules

VIOLATIONS = """\
from __future__ import annotations

import ssl

def tls() -> None:
    ssl._create_unverified_context()
    import httpx
    httpx.get("https://example.com", verify=False)

def cors() -> None:
    from lexigram.web.cors import allow
    allow(allow_origins=["*"], allow_credentials=True)

def jwt() -> None:
    from jose import jwt
    jwt.decode(token, key, algorithms=["none"])

API_SECRET = "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6"
"""


def _write_violations(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "workspace"\n\n[tool.uv.workspace]\nmembers = ["lexigram-web"]\n',
        encoding="utf-8",
    )
    package_root = root / "lexigram-web"
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram-web"\n', encoding="utf-8"
    )
    src = package_root / "src" / "lexigram" / "web"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "bad_security.py").write_text(VIOLATIONS, encoding="utf-8")


def test_security_rules_fire_on_violations(tmp_path: Path) -> None:
    _write_violations(tmp_path)
    findings = run_rules(tmp_path, packages=("lexigram-web",)).findings
    rule_ids = {f.rule_id for f in findings if f.rule_id.startswith("sec-")}
    assert rule_ids == {
        "sec-tls-verify-disabled",
        "sec-hardcoded-secret",
        "sec-cors-wildcard-credentials",
        "sec-jwt-verification-disabled",
    }


def test_security_rules_ignore_safe_code(tmp_path: Path) -> None:
    package_root = tmp_path / "lexigram"
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram"\n', encoding="utf-8"
    )
    src = package_root / "src" / "lexigram"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "safe.py").write_text(
        'from __future__ import annotations\n\n'
        'import ssl\n\n'
        'def safe() -> None:\n'
        '    context = ssl.create_default_context()\n'
        '    del context\n'
        'SESSION_COOKIE = "example-session"\n'
        'ERROR_MSG_INSECURE_PASSWORD = "The supplied password was rejected"\n'
        'STABILITY_API_KEY_SECRET_NAME = "stability_api_key"\n'
        'DUMMY_PASSWORD_HASH = "d3adbeefd3adbeefd3adbeefd3adbeef"\n'
        'PASSWORD_RESET_REQUESTED = "password_reset_requested"\n',
        encoding="utf-8",
    )
    findings = run_rules(tmp_path, packages=("lexigram",)).findings
    assert all(not f.rule_id.startswith("sec-") for f in findings)
