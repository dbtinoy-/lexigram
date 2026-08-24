"""GraphQL protocol definitions.

Protocols for GraphQL execution, schema building, data loading,
resolvers, and subscriptions.
"""

from __future__ import annotations

from lexigram.contracts.graphql.protocols.execution import (
    DEFAULT_SUBSCRIPTIONS_PATH as DEFAULT_SUBSCRIPTIONS_PATH,
)
from lexigram.contracts.graphql.protocols.execution import (
    DataLoaderProtocol as DataLoaderProtocol,
)
from lexigram.contracts.graphql.protocols.execution import (
    EntityResolverProtocol as EntityResolverProtocol,
)
from lexigram.contracts.graphql.protocols.execution import (
    GraphQLControllerProtocol as GraphQLControllerProtocol,
)
from lexigram.contracts.graphql.protocols.execution import (
    GraphQLExecutorProtocol as GraphQLExecutorProtocol,
)
from lexigram.contracts.graphql.protocols.execution import (
    ResolverProtocol as ResolverProtocol,
)
from lexigram.contracts.graphql.protocols.execution import (
    SchemaBuilderProtocol as SchemaBuilderProtocol,
)
from lexigram.contracts.graphql.protocols.subscription import (
    DirectiveHandlerProtocol as DirectiveHandlerProtocol,
)
from lexigram.contracts.graphql.protocols.subscription import (
    MutationHandlerProtocol as MutationHandlerProtocol,
)
from lexigram.contracts.graphql.protocols.subscription import (
    SubscriptionAuthHandlerProtocol as SubscriptionAuthHandlerProtocol,
)
from lexigram.contracts.graphql.protocols.subscription import (
    SubscriptionHandlerProtocol as SubscriptionHandlerProtocol,
)
from lexigram.contracts.graphql.protocols.subscription import (
    WebSocketTransportProtocol as WebSocketTransportProtocol,
)
from lexigram.contracts.graphql.protocols.types import (
    ErrorFormatterProtocol as ErrorFormatterProtocol,
)
from lexigram.contracts.graphql.protocols.types import (
    GraphQLPrincipalResolverProtocol as GraphQLPrincipalResolverProtocol,
)
from lexigram.contracts.graphql.protocols.types import (
    GraphQLRequestProtocol as GraphQLRequestProtocol,
)
from lexigram.contracts.graphql.protocols.types import (
    IntrospectionHandlerProtocol as IntrospectionHandlerProtocol,
)
from lexigram.contracts.graphql.protocols.types import (
    ValidationRuleProtocol as ValidationRuleProtocol,
)

__all__ = [
    "DEFAULT_SUBSCRIPTIONS_PATH",
    "DataLoaderProtocol",
    "DirectiveHandlerProtocol",
    "EntityResolverProtocol",
    "ErrorFormatterProtocol",
    "GraphQLControllerProtocol",
    "GraphQLExecutorProtocol",
    "GraphQLPrincipalResolverProtocol",
    "GraphQLRequestProtocol",
    "IntrospectionHandlerProtocol",
    "MutationHandlerProtocol",
    "ResolverProtocol",
    "SchemaBuilderProtocol",
    "SubscriptionAuthHandlerProtocol",
    "SubscriptionHandlerProtocol",
    "ValidationRuleProtocol",
    "WebSocketTransportProtocol",
]
