"""PromptService — centralised template management, rendering, and escaping.

Design decisions
----------------
* Templates are loaded **at construction time** (boot phase).  Hot-reload is
  out of scope; the service is read-only at runtime.
* Templates are addressed by ``(name, version)``.  ``version="latest"`` resolves
  to the most recently registered version for that name.
* Variable substitution uses Python ``str.format_map`` (``{variable}`` syntax)
  so it is compatible with the existing :class:`~lexigram.ai.prompt.rendering.engine.PromptRenderer`.
* Provider-specific escaping is applied to variable *values* **before**
  substitution so that special characters in values do not break the template.
  Full escaping rules are stubbed — see ``_apply_provider_escaping``.
* The observability hook (``PromptObserverProtocol``) is called synchronously
  after every successful render.  Exceptions from the observer are caught and
  logged as warnings so they never break the caller.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lexigram.ai.prompt.exceptions import (
    PromptConfigError,
    PromptNotFoundError,
    PromptRenderError,
)
from lexigram.ai.prompt.rendering.engine import PromptRenderer, RenderFormat
from lexigram.ai.prompt.service.models import (
    LLMProvider,
    PromptRenderRequest,
    PromptRenderResult,
    PromptTemplate,
)
from lexigram.ai.prompt.service.observer import (
    NoOpPromptObserver,
    PromptObserverProtocol,
)
from lexigram.logging import get_logger

logger = get_logger(__name__)

# Sentinel used internally when resolving "latest".
_LATEST = "latest"


@runtime_checkable
class PromptServiceProtocol(Protocol):
    """Structural protocol for PromptService.

    Inject this type in DI containers so consumers don't depend on the
    concrete class.
    """

    def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        """Render a named prompt template.

        Args:
            request: Lookup key + variable values.

        Returns:
            The rendered result.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                No template with the given ``(name, version)`` is registered.
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required variable is missing from the request.
        """
        ...

    def get_template(self, name: str, version: str = _LATEST) -> PromptTemplate:
        """Return the :class:`~lexigram.ai.prompt.service.models.PromptTemplate`
        for ``(name, version)`` without rendering it."""
        ...

    def list_templates(self) -> list[tuple[str, str]]:
        """Return all registered ``(name, version)`` pairs."""
        ...


class PromptService:
    """Injectable service for loading, versioning, and rendering prompt templates.

    Instantiate at boot time (via the DI provider) with one or more
    :class:`~lexigram.ai.prompt.service.loader.PromptLoaderProtocol` sources.

    Args:
        templates: Pre-built list of :class:`~lexigram.ai.prompt.service.models.PromptTemplate`
                   objects.  Pass an empty list and call :meth:`_register` if
                   you are building the service manually.
        observer:  Optional observability hook.  Defaults to
                   :class:`~lexigram.ai.prompt.service.observer.NoOpPromptObserver`.

    Example::

        from lexigram.ai.prompt.service import (
            DictPromptLoader, PromptService, PromptRenderRequest
        )

        loader = DictPromptLoader([
            {
                "name": "greeting",
                "version": "v1",
                "content": "Hello, {name}!",
                "required_variables": ["name"],
                "provider": "anthropic",
            }
        ])
        service = PromptService(loader.load())
        result = service.render(PromptRenderRequest(name="greeting", variables={"name": "Alice"}))
        print(result.rendered)  # Hello, Alice!
    """

    def __init__(
        self,
        templates: list[PromptTemplate],
        observer: PromptObserverProtocol | None = None,
    ) -> None:
        self._observer: PromptObserverProtocol = observer or NoOpPromptObserver()
        # _store: name → {version → PromptTemplate}
        self._store: dict[str, dict[str, PromptTemplate]] = {}
        # _latest: name → most-recently-registered version string
        self._latest: dict[str, str] = {}

        for tmpl in templates:
            self._register(tmpl)

        logger.debug(
            "prompt_service_initialised",
            template_count=sum(len(v) for v in self._store.values()),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        """Render a named prompt template.

        Args:
            request: Lookup key, variables, and optional pinned version.

        Returns:
            :class:`~lexigram.ai.prompt.service.models.PromptRenderResult`

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                No template with the requested ``(name, version)``.
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required variable is missing or substitution fails.
        """
        tmpl = self.get_template(request.name, request.version)
        resolved = self._resolve_variables(tmpl, request.variables)
        escaped = self._apply_provider_escaping(tmpl.provider, resolved)
        rendered = self._substitute(tmpl.content, escaped, tmpl.name, tmpl.engine)

        result = PromptRenderResult(
            name=tmpl.name,
            version=tmpl.version,
            rendered=rendered,
            provider=tmpl.provider,
        )

        self._notify_observer(tmpl.name, tmpl.version, resolved, rendered)
        return result

    def get_template(self, name: str, version: str = _LATEST) -> PromptTemplate:
        """Look up a template by name and optional version.

        Args:
            name: Template name.
            version: Version string or ``"latest"`` (default).

        Returns:
            The matching :class:`~lexigram.ai.prompt.service.models.PromptTemplate`.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                Name or version is not registered.
        """
        versions = self._store.get(name)
        if versions is None:
            available = sorted(self._store.keys())
            raise PromptNotFoundError(
                f"No prompt template registered under '{name}'. "
                f"Available names: {available!r}"
            )

        resolved_version = self._latest[name] if version == _LATEST else version
        tmpl = versions.get(resolved_version)
        if tmpl is None:
            raise PromptNotFoundError(
                f"Template '{name}' version '{resolved_version}' not found. "
                f"Available versions: {sorted(versions.keys())!r}"
            )
        return tmpl

    def list_templates(self) -> list[tuple[str, str]]:
        """Return all ``(name, version)`` pairs sorted by name then version."""
        pairs: list[tuple[str, str]] = []
        for name, versions in sorted(self._store.items()):
            for version in sorted(versions.keys()):
                pairs.append((name, version))
        return pairs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, tmpl: PromptTemplate) -> None:
        """Store a template and update the 'latest' pointer."""
        versions = self._store.setdefault(tmpl.name, {})
        versions[tmpl.version] = tmpl
        # Last-registered wins for "latest".
        self._latest[tmpl.name] = tmpl.version

    def _resolve_variables(
        self,
        tmpl: PromptTemplate,
        supplied: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge supplied variables with optional defaults and enforce required vars.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required variable was not supplied.
        """
        resolved: dict[str, Any] = dict(tmpl.optional_defaults)
        resolved.update(supplied)

        missing = [v for v in tmpl.required_variables if v not in resolved]
        if missing:
            raise PromptRenderError(
                f"Template '{tmpl.name}' v{tmpl.version}: "
                f"missing required variable(s): {missing!r}. "
                f"Supplied: {sorted(supplied.keys())!r}"
            )

        return resolved

    def _substitute(
        self,
        content: str,
        variables: dict[str, Any],
        template_name: str,
        engine: str = "format",
    ) -> str:
        """Perform variable substitution using the template's declared engine.

        ``engine="format"`` (default) uses Python ``str.format_map``.
        ``engine="jinja2"`` uses Jinja2 rendering (loops, filters, conditionals).

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A placeholder in the template has no corresponding variable, or
                the Jinja2 template contains a syntax/undefined-variable error.
            :class:`~lexigram.ai.prompt.exceptions.PromptConfigError`:
                ``engine`` is set to an unknown value.
        """
        if engine == "jinja2":
            renderer = PromptRenderer(RenderFormat.JINJA2)
            try:
                return renderer.render(content, variables)
            except PromptRenderError:
                raise
            except Exception as exc:
                raise PromptRenderError(
                    f"Template '{template_name}': Jinja2 rendering error — {exc}"
                ) from exc

        if engine == "format":
            try:
                return content.format_map(_StrictFormatMap(variables))
            except KeyError as exc:
                raise PromptRenderError(
                    f"Template '{template_name}': placeholder {exc} has no value. "
                    f"Supplied variables: {sorted(variables.keys())!r}"
                ) from exc
            except ValueError as exc:
                raise PromptRenderError(
                    f"Template '{template_name}': substitution error — {exc}"
                ) from exc

        raise PromptConfigError(
            f"Template '{template_name}': unknown engine {engine!r}. "
            f"Valid values: ['format', 'jinja2']"
        )

    @staticmethod
    def _apply_provider_escaping(
        provider: LLMProvider,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply provider-specific escaping to variable *values* before substitution.

        Status: scaffolded seam — minimal real escaping is in place; full
        provider-specific rules are a TODO.

        Anthropic:
            Values are passed through as-is.  A future implementation would
            wrap values that contain ``{`` / ``}`` or XML-special characters in
            ``<parameter name="…">…</parameter>`` tags to prevent prompt
            injection.  The seam is here; the full rule set is out of scope.

        OpenAI / Azure:
            Literal ``{`` and ``}`` characters inside values are escaped to
            ``{{`` and ``}}`` to prevent them being interpreted as format
            placeholders by downstream callers that re-template the output.

        Generic:
            No escaping.
        """
        if provider in (LLMProvider.GENERIC, LLMProvider.ANTHROPIC):
            # TODO(LEX-009): Anthropic — wrap values in <parameter> XML tags
            # when the value contains characters that could break the Claude
            # system prompt (e.g. angle brackets or unbalanced braces).
            return variables

        if provider in (LLMProvider.OPENAI, LLMProvider.AZURE):
            escaped: dict[str, Any] = {}
            for key, val in variables.items():
                if isinstance(val, str):
                    # Escape literal braces so they survive any subsequent
                    # str.format_map calls on the rendered output.
                    escaped[key] = val.replace("{", "{{").replace("}", "}}")
                else:
                    escaped[key] = val
            return escaped

        # Unreachable with current enum, but safe fallback.
        return variables  # pragma: no cover

    def _notify_observer(
        self,
        name: str,
        version: str,
        variables: dict[str, Any],
        rendered_output: str,
    ) -> None:
        """Call the observer, swallowing any exceptions."""
        try:
            self._observer.on_render(name, version, variables, rendered_output)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "prompt_observer_error",
                template=name,
                version=version,
                error=str(exc),
            )


class _StrictFormatMap(dict):
    """``str.format_map`` helper that raises ``KeyError`` for missing placeholders."""

    def __missing__(self, key: str) -> str:
        raise KeyError(key)


__all__ = ["PromptService", "PromptServiceProtocol"]
