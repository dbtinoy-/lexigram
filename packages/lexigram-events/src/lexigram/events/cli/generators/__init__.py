"""Events CLI generators."""

from lexigram.events.cli.generators.command_handler import CommandHandlerGenerator
from lexigram.events.cli.generators.event_generator import EventGenerator
from lexigram.events.cli.generators.event_handler import EventHandlerGenerator
from lexigram.events.cli.generators.projection import ProjectionGenerator
from lexigram.events.cli.generators.query_handler import QueryHandlerGenerator
from lexigram.events.cli.generators.saga import SagaGenerator

__all__ = [
    "CommandHandlerGenerator",
    "EventGenerator",
    "EventHandlerGenerator",
    "ProjectionGenerator",
    "QueryHandlerGenerator",
    "SagaGenerator",
]
