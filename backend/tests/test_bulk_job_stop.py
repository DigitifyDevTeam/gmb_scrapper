from app.models.enums import SearchStatus
from app.workers.bulk_cancel import is_bulk_cancel_requested
from app.workers.job_runner import BulkJobState, JobRunner


def test_request_bulk_stop_marks_job_stopped_immediately() -> None:
    runner = JobRunner()
    state = BulkJobState(
        job_id="bulk-test",
        country="France",
        target_count=100,
        status=SearchStatus.RUNNING,
        current_city="Paris",
        current_category="Restaurant",
    )
    runner.register_bulk_job(state)
    register_bulk_cancel(state.job_id)

    stopped = runner.request_bulk_stop(state.job_id)

    assert stopped.status == SearchStatus.STOPPED
    assert stopped.stop_requested is True
    assert stopped.pause_requested is False
    assert stopped.finished_at is not None
    assert stopped.current_city is None
    assert stopped.current_category is None
    assert runner.get_active_bulk_job() is None
    assert is_bulk_cancel_requested(state.job_id) is True


def test_request_bulk_stop_is_idempotent() -> None:
    runner = JobRunner()
    state = BulkJobState(
        job_id="bulk-test-2",
        country="France",
        target_count=100,
        status=SearchStatus.PAUSED,
    )
    runner.register_bulk_job(state)
    register_bulk_cancel(state.job_id)

    first = runner.request_bulk_stop(state.job_id)
    second = runner.request_bulk_stop(state.job_id)

    assert first.status == SearchStatus.STOPPED
    assert second.status == SearchStatus.STOPPED
    assert second.finished_at == first.finished_at
