from lexigram.web.exceptions import NotFoundError


class RunNotFoundError(NotFoundError):
    """404 — Run not found."""

    def __init__(self, run_id: str) -> None:
        super().__init__(detail=f"Run {run_id} not found")
        self.run_id = run_id
