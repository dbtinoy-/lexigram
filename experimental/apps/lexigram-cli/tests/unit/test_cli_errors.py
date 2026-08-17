"""Tests for CLI error hierarchy."""

from lexigram.cli.exceptions import CliError


class TestCliError:
    def test_basic_error(self):
        err = CliError("something broke")
        assert "something broke" in str(err)
        assert err.message == "something broke"

    def test_error_with_hints(self):
        err = CliError(
            "Database connection failed",
            causes=["PostgreSQL is not running", "Database does not exist"],
            suggestions=["Start PostgreSQL: sudo systemctl start postgresql",
                         "Check config: lexigram config show database"],
        )
        assert err.causes == ["PostgreSQL is not running", "Database does not exist"]
        assert len(err.suggestions) == 2

    def test_error_with_no_extras(self):
        err = CliError("simple error")
        assert err.causes == []
        assert err.suggestions == []

    def test_error_inherits_lexigram_error(self):
        from lexigram.contracts.exceptions import LexigramError
        err = CliError("test")
        assert isinstance(err, LexigramError)

    def test_config_not_found_error(self):
        from lexigram.cli.exceptions import ConfigNotFoundError
        err = ConfigNotFoundError()
        assert "application.yaml" in err.message
        assert any("lexigram init" in s for s in err.suggestions)

    def test_provider_not_installed_error(self):
        from lexigram.cli.exceptions import ProviderNotInstalledError
        err = ProviderNotInstalledError("lexigram-sql")
        assert "lexigram-sql" in err.message
