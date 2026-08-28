from __future__ import annotations

import pathlib
import tomllib

import pytest

from lexigram.contracts.cli.protocols import CliContributorProtocol
from lexigram.web.cli.contributor import WebCliContributor
from lexigram.web.cli.generators.controller import ControllerGenerator
from lexigram.web.cli.generators.exception_filter import ExceptionFilterGenerator
from lexigram.web.cli.generators.interceptor import InterceptorGenerator
from lexigram.web.cli.generators.resource import ResourceGenerator


def test_web_contributor_implements_protocol_shape() -> None:
    contributor = WebCliContributor()

    assert isinstance(contributor, CliContributorProtocol)
    assert contributor.contributor_id == "web"


def test_web_contributor_exposes_expected_generators() -> None:
    contributor = WebCliContributor()

    assert {definition.name for definition in contributor.get_generators()} == {
        "controller",
        "resource",
        "middleware",
        "graphql",
        "webhook",
        "websocket",
        "exception_filter",
        "interceptor",
    }


def test_web_contributor_paths_are_package_local() -> None:
    contributor = WebCliContributor()

    assert {
        definition.generator_path for definition in contributor.get_generators()
    } == {
        "lexigram.web.cli.generators.controller:ControllerGenerator",
        "lexigram.web.cli.generators.resource:ResourceGenerator",
        "lexigram.web.cli.generators.middleware:MiddlewareGenerator",
        "lexigram.web.cli.generators.graphql:GraphQLGenerator",
        "lexigram.web.cli.generators.webhook:WebhookGenerator",
        "lexigram.web.cli.generators.websocket:WebSocketHandlerGenerator",
        "lexigram.web.cli.generators.exception_filter:ExceptionFilterGenerator",
        "lexigram.web.cli.generators.interceptor:InterceptorGenerator",
    }


def test_web_pyproject_declares_cli_contributor_entry_point() -> None:
    pyproject_path = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())
    group = data["project"]["entry-points"]["lexigram.cli.contributors"]

    assert group["web"] == "lexigram.web.cli.contributor:WebCliContributor"


def test_exception_filter_generator_defaults() -> None:
    generator = ExceptionFilterGenerator()

    assert generator.name == "exception_filter"
    assert generator.default_output_dir == "src/filters"


def test_interceptor_generator_defaults() -> None:
    generator = InterceptorGenerator()

    assert generator.name == "interceptor"
    assert generator.default_output_dir == "src/interceptors"


def test_resource_generator_uses_package_local_controller() -> None:
    generator = ResourceGenerator()

    assert generator.controller_generator_class is ControllerGenerator


@pytest.mark.parametrize(
    ("name", "default_output_dir"),
    [
        ("controller", "src/controllers"),
        ("resource", "src"),
        ("middleware", "src/middleware"),
        ("graphql", "src/graphql"),
        ("webhook", "src/webhooks"),
        ("websocket", "src/websocket"),
        ("exception_filter", "src/filters"),
        ("interceptor", "src/interceptors"),
    ],
)
def test_web_generator_defaults(name: str, default_output_dir: str) -> None:
    contributor = WebCliContributor()
    definitions = {
        definition.name: definition for definition in contributor.get_generators()
    }

    assert definitions[name].default_output_dir == default_output_dir
    assert definitions[name].contributor == "web"
    assert definitions[name].category == "web"
