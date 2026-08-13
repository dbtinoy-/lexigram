"""GraphQL package CLI contributor and generators."""

from __future__ import annotations

from lexigram.graphql.cli.contributor import GraphQLCliContributor
from lexigram.graphql.cli.generators.dataloader import DataLoaderGenerator

__all__ = ["GraphQLCliContributor", "DataLoaderGenerator"]
