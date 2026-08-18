from __future__ import annotations

from pathlib import Path
import tomllib

from dev.audit.generators.base import MarkdownAuditGenerator


class IntegrationsAuditGenerator(MarkdownAuditGenerator):
    """Generate a lightweight integrations audit."""

    name = "integrations"
    description = "Generate AUDIT_INTEGRATIONS.md from backend directories and dependency hints."
    output_file = "AUDIT_INTEGRATIONS.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render integrations markdown."""

        package_rows = [_integration_row(path) for path in self.iter_package_roots(root=root)]
        package_rows = [row for row in package_rows if row["implementations"] or row["services"]]

        markdown = """# AUDIT_INTEGRATIONS.md — Lexigram Framework Integrations

> **Source**: Backend-style directories and dependency hints from `pyproject.toml`.

---

## Packages With Integration Signals

"""
        markdown += f"- Packages with integration signals: {len(package_rows)}\n\n"
        markdown += "| Package | Implementations | External Services |\n"
        markdown += "|---------|-----------------|-------------------|\n"
        for row in package_rows:
            implementations = ", ".join(row["implementations"]) or "-"
            services = ", ".join(row["services"]) or "-"
            markdown += f"| `{row['name']}` | {implementations} | {services} |\n"
        markdown += "\n"
        return markdown


def _integration_row(package_path: Path) -> dict[str, list[str] | str]:
    """Collect minimal integration signals for one package."""

    implementations: set[str] = set()
    for directory_name in ("backends", "adapters", "clients", "drivers"):
        for match in package_path.glob(f"src/**/{directory_name}"):
            if not match.is_dir():
                continue
            for child in sorted(match.iterdir()):
                if child.name.startswith("_") or child.name == "__pycache__":
                    continue
                if child.is_dir():
                    implementations.add(child.name)
                if child.is_file() and child.suffix == ".py" and child.stem != "__init__":
                    implementations.add(child.stem)

    services: set[str] = set()
    pyproject_path = package_path / "pyproject.toml"
    if pyproject_path.is_file():
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
        dependencies = list(data.get("project", {}).get("dependencies", []))
        optional_dependencies = data.get("project", {}).get("optional-dependencies", {})
        for extra_deps in optional_dependencies.values():
            dependencies.extend(extra_deps)
        for dependency in dependencies:
            normalized = str(dependency).lower()
            for token, service in _SERVICE_MAP.items():
                if token in normalized:
                    services.add(service)

    return {
        "name": package_path.name,
        "implementations": sorted(implementations),
        "services": sorted(services),
    }


_SERVICE_MAP = {
    "redis": "Redis",
    "postgres": "PostgreSQL",
    "psycopg": "PostgreSQL",
    "asyncpg": "PostgreSQL",
    "sqlite": "SQLite",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "nats": "NATS",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "qdrant": "Qdrant",
    "weaviate": "Weaviate",
    "chroma": "Chroma",
    "s3": "S3",
}
