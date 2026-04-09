from lexigram.multimedia.jobs import JobHandle


def test_job_handle_wraps_idempotency_result_fields() -> None:
    class _FakeIdempotencyResult:
        task_id = "abc-123"
        status = "submitted"

    handle = JobHandle.from_idempotency_result(_FakeIdempotencyResult())

    assert handle.job_id == "abc-123"
    assert handle.status == "submitted"
    assert handle.is_duplicate is False


def test_job_handle_defaults_is_duplicate_true_for_completed_status() -> None:
    class _FakeIdempotencyResult:
        task_id = "abc-123"
        status = "completed"

    handle = JobHandle.from_idempotency_result(_FakeIdempotencyResult())

    assert handle.is_duplicate is True


def test_job_handle_accepts_explicit_is_duplicate_override() -> None:
    class _FakeIdempotencyResult:
        task_id = "abc-123"
        status = "submitted"

    handle = JobHandle.from_idempotency_result(_FakeIdempotencyResult(), is_duplicate=True)

    assert handle.is_duplicate is True
