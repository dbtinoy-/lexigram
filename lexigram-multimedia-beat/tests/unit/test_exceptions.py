from lexigram.contracts.multimedia.exceptions import BeatAnalysisError
from lexigram.multimedia.beat.exceptions import (
    BeatAnalysisConnectionError,
    BeatAnalysisDecodeError,
    BeatAnalysisTimeoutError,
)


def test_beat_analysis_leaf_errors_extend_beat_analysis_error() -> None:
    for exc_cls, code in (
        (BeatAnalysisTimeoutError, "LEX_ERR_MM_BEAT_001"),
        (BeatAnalysisConnectionError, "LEX_ERR_MM_BEAT_002"),
        (BeatAnalysisDecodeError, "LEX_ERR_MM_BEAT_003"),
    ):
        assert issubclass(exc_cls, BeatAnalysisError)
        assert exc_cls._code == code
