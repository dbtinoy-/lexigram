"""Served-model catalog for the gateway's ``/v1/models`` surface.

``ModelCatalogService`` aggregates the client-visible model aliases from
the configured channel table into the three wire formats' list and
detail shapes (OpenAI, Anthropic, Gemini).  It is a pure function of the
channel registry's static table and runtime overrides: drained and
config-disabled channels contribute nothing, aliases are deduplicated,
and the payloads never leak upstream URLs or credentials.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry

__all__ = ["ModelCatalogService"]

_OWNED_BY = "lexigram"
"""Owner label reported in OpenAI model list entries."""

_CREATED_AT = "1970-01-01T00:00:00Z"
"""Fixed created-at stamp reported in Anthropic model entries."""

_GENERATION_METHODS = ("generateContent",)
"""Generation methods reported for Gemini model entries."""


class ModelCatalogService:
    """Aggregate served model aliases per wire format.

    Args:
        registry: The channel registry whose enabled, non-drained
            channels define the served model set.
    """

    def __init__(self, registry: RelayChannelRegistry) -> None:
        """Bind the catalog to the channel registry.

        Args:
            registry: The channel registry backing the model set.
        """
        self._registry = registry

    def list_openai(self) -> dict[str, Any]:
        """Return the OpenAI ``/v1/models`` list payload.

        Returns:
            A list payload with one entry per served alias, sorted.
        """
        return {
            "object": "list",
            "data": [
                {
                    "id": alias,
                    "object": "model",
                    "created": 0,
                    "owned_by": _OWNED_BY,
                }
                for alias in self._served_models()
            ],
        }

    def list_claude(self) -> dict[str, Any]:
        """Return the Anthropic ``/v1/models`` list payload.

        Returns:
            A list payload with one entry per served alias, sorted.
        """
        return {
            "data": [
                {
                    "type": "model",
                    "id": alias,
                    "display_name": alias,
                    "created_at": _CREATED_AT,
                }
                for alias in self._served_models()
            ],
        }

    def list_gemini(self) -> dict[str, Any]:
        """Return the Gemini ``/v1beta/models`` list payload.

        Returns:
            A list payload with one model entry per served alias, sorted.
        """
        return {
            "models": [
                {
                    "name": f"models/{alias}",
                    "displayName": alias,
                    "supportedGenerationMethods": list(_GENERATION_METHODS),
                }
                for alias in self._served_models()
            ],
        }

    def model_exists(self, alias: str) -> bool:
        """Return whether *alias* is served by any enabled channel.

        Args:
            alias: The model alias to look up.

        Returns:
            ``True`` when the alias is served, ``False`` otherwise.
        """
        return alias in self._served_models()

    def openai_detail(self, alias: str) -> dict[str, Any] | None:
        """Return the OpenAI model detail payload for *alias*.

        Args:
            alias: The model alias to describe.

        Returns:
            The detail payload, or ``None`` when the alias is not served.
        """
        if not self.model_exists(alias):
            return None
        return {
            "id": alias,
            "object": "model",
            "created": 0,
            "owned_by": _OWNED_BY,
        }

    def gemini_detail(self, alias: str) -> dict[str, Any] | None:
        """Return the Gemini model detail payload for *alias*.

        Args:
            alias: The model alias to describe.

        Returns:
            The detail payload, or ``None`` when the alias is not served.
        """
        if not self.model_exists(alias):
            return None
        return {
            "name": f"models/{alias}",
            "displayName": alias,
            "supportedGenerationMethods": list(_GENERATION_METHODS),
        }

    def _served_models(self) -> tuple[str, ...]:
        """Return the sorted, deduplicated served alias set."""
        served: set[str] = set()
        for channel in self._registry.channels:
            if channel.enabled and self._registry.runtime_enabled().get(
                channel.name, True
            ):
                served.update(channel.models)
        return tuple(sorted(served))
