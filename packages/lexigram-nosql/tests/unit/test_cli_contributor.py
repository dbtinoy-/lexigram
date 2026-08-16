from __future__ import annotations

from lexigram.contracts.cli.types import GeneratorDefinition
from lexigram.nosql.cli.contributor import NoSqlCliContributor


class TestNoSqlCliContributor:
    def setup_method(self) -> None:
        self.contributor = NoSqlCliContributor()

    def test_contributor_id(self) -> None:
        assert self.contributor.contributor_id == "nosql"

    def test_get_generators_returns_document_repo(self) -> None:
        generators = self.contributor.get_generators()
        assert len(generators) == 1
        gen = generators[0]
        assert isinstance(gen, GeneratorDefinition)
        assert gen.name == "document_repo"
        assert gen.contributor == "nosql"

    def test_get_commands_returns_empty(self) -> None:
        assert self.contributor.get_commands() == []

    def test_get_health_checks_returns_nosql_check(self) -> None:
        checks = self.contributor.get_health_checks()
        assert len(checks) == 1
        assert checks[0].name == "nosql_connection"
        assert checks[0].contributor == "nosql"
        assert checks[0].category == "database"
        assert checks[0].timeout == 10.0

    def test_get_doctor_checks_returns_empty(self) -> None:
        assert self.contributor.get_doctor_checks() == []

    def test_get_shell_context_returns_empty(self) -> None:
        assert self.contributor.get_shell_context() == []

    def test_get_hooks_returns_empty(self) -> None:
        assert self.contributor.get_hooks() == []
