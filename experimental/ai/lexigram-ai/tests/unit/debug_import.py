from lexigram.vector.backends import pgvector
from lexigram.logging import get_logger


logger = get_logger(__name__)


def test_import_location():
    logger.debug("pgvector file: %s", pgvector.__file__)
    assert pgvector.__file__ is not None
