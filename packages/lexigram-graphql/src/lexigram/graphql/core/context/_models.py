"""GraphQL request/response/error domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar
import uuid

from lexigram.contracts.auth import AuthenticatorProtocol
from lexigram.contracts.core import IdGeneratorProtocol
from lexigram.contracts.graphql import (
    GraphQLPrincipal,
    GraphQLPrincipalResolverProtocol,
)
from lexigram.domain import DomainModel
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.validation import Field

if TYPE_CHECKING:
    from lexigram.graphql.config import GraphQLConfig

logger = get_logger(__name__)


T = TypeVar("T")


@dataclass(init=False)
class GraphQLRequest(DomainModel):
    """GraphQL request model.

    Represents an incoming GraphQL request with query,
    variables, and operation name.

    Attributes:
        query: The GraphQL query string.
        variables: Variables for the query.
        operation_name: Name of the operation to execute.
        extensions: Optional extensions data.
    """

    query: str = Field(..., description="GraphQL query string")
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Query variables",
    )
    operation_name: str | None = Field(
        default=None,
        description="Operation name to execute",
    )
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description="Request extensions",
    )

    model_config = {"frozen": False}


@dataclass(init=False)
class GraphQLErrorPayload(DomainModel):
    """GraphQL error payload model.

    G-09 FIX: Renamed from GraphQLError to GraphQLErrorPayload to avoid
    naming collision with the GraphQLError in exceptions.py.

    Represents a GraphQL error following the spec.

    Attributes:
        message: Human-readable error message.
        locations: Source locations of the error.
        path: Path to the field that caused the error.
        extensions: Additional error information.
    """

    message: str = Field(..., description="Error message")
    locations: list[dict[str, int]] | None = Field(
        default=None,
        description="Source locations",
    )
    path: list[str | int] | None = Field(
        default=None,
        description="Path to the error",
    )
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description="Error extensions",
    )


@dataclass(init=False)
class GraphQLResponse(DomainModel, Generic[T]):
    """GraphQL response model.

    Represents a GraphQL response with data and/or errors.

    Attributes:
        data: The result data.
        errors: List of errors if any occurred.
        extensions: Optional response extensions.
    """

    data: T | None = Field(default=None, description="Response data")
    errors: list[GraphQLErrorPayload] | None = Field(
        default=None,
        description="List of errors",
    )
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description="Response extensions",
    )
    http_headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP response headers (e.g. Cache-Control, Vary) set by the executor",
    )

    @property
    def has_errors(self) -> bool:
        """Check if response has errors."""
        return self.errors is not None and len(self.errors) > 0

    @property
    def is_successful(self) -> bool:
        """Check if response is successful."""
        return not self.has_errors

    def add_error(
        self,
        message: str,
        path: list[str | int] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """Add an error to the response.

        Args:
            message: Error message.
            path: Path to the error.
            extensions: Additional error data.
        """
        if self.errors is None:
            self.errors = []

        self.errors.append(
            GraphQLErrorPayload(
                message=message,
                path=path,
                extensions=extensions or {},
            ),
        )
