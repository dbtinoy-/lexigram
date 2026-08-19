from __future__ import annotations

from dev.audit.generators import env_vars as env_vars_audit


def test_env_audit_includes_non_config_sources_appendix() -> None:
    env_var_def = env_vars_audit.EnvVarDef
    generate_markdown = env_vars_audit.generate_markdown

    sample_packages = {
        "lexigram-web": [
            env_var_def(
                package="lexigram-web",
                env_var="LEX_WEB__HOST",
                type_annotation="str",
                default_value='"127.0.0.1"',
                description="Host binding for web server",
                source_file="lexigram-web/src/lexigram/web/config.py",
                source_class="WebConfig",
                source_field_path="host",
            )
        ]
    }

    markdown = generate_markdown(sample_packages)

    assert "## Non-Config ENV Sources" in markdown
    assert "`LEX_DEBUG`" in markdown
    assert "lexigram/src/lexigram/logging/debug.py" in markdown
