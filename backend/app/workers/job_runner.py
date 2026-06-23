import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.models.enums import SearchStatus
from app.workers.bulk_cancel import clear_bulk_cancel, register_bulk_cancel, signal_bulk_cancel

logger = logging.getLogger(__name__)

JobCallable = Callable[[], Awaitable[None]]

_ACTIVE_BULK_STATUSES = frozenset({SearchStatus.RUNNING, SearchStatus.PAUSED})


@dataclass
class JobState:
    job_id: str
    search_id: int
    status: SearchStatus = SearchStatus.PENDING
    prospects_found: int = 0
    prospects_saved: int = 0
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    _task: asyncio.Task[None] | None = field(default=None, repr=False)


@dataclass
class BulkJobState:
    job_id: str
    country: str
    target_count: int
    status: SearchStatus = SearchStatus.PENDING
    total_queries: int = 0
    completed_queries: int = 0
    prospects_found: int = 0
    prospects_saved: int = 0
    prospects_saved_with_website: int = 0
    prospects_saved_total: int = 0
    prospects_skipped_duplicates: int = 0
    current_city: str | None = None
    current_category: str | None = None
    pause_requested: bool = False
    stop_requested: bool = False
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    _task: asyncio.Task[None] | None = field(default=None, repr=False)


class JobRunner:
    """
    In-process asyncio job manager.

    Designed as an interface boundary so Celery/ARQ can replace it later.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._bulk_jobs: dict[str, BulkJobState] = {}

    def start_job(self, job_id: str, search_id: int, coro_factory: JobCallable) -> JobState:
        if job_id in self._jobs and self._jobs[job_id].status == SearchStatus.RUNNING:
            return self._jobs[job_id]

        state = JobState(job_id=job_id, search_id=search_id, status=SearchStatus.RUNNING)
        self._jobs[job_id] = state

        async def wrapped() -> None:
            try:
                await coro_factory()
                if state.status != SearchStatus.FAILED:
                    state.status = SearchStatus.COMPLETED
            except Exception as exc:
                logger.exception("Job %s failed", job_id)
                state.status = SearchStatus.FAILED
                state.error = str(exc) or repr(exc)
            finally:
                state.finished_at = datetime.now(timezone.utc)

        state._task = asyncio.create_task(wrapped())
        return state

    def start_bulk_job(
        self,
        coro_factory: JobCallable,
        *,
        country: str,
        target_count: int,
        job_id: str | None = None,
    ) -> BulkJobState:
        active = self.get_active_bulk_job()
        if active is not None:
            return active

        resolved_job_id = job_id or f"bulk-{uuid4().hex[:12]}"
        state = BulkJobState(
            job_id=resolved_job_id,
            country=country,
            target_count=target_count,
            status=SearchStatus.RUNNING,
        )
        self._bulk_jobs[resolved_job_id] = state
        register_bulk_cancel(resolved_job_id)
        self.start_bulk_job_task(state, coro_factory)
        return state

    def register_bulk_job(self, state: BulkJobState) -> None:
        self._bulk_jobs[state.job_id] = state

    def start_bulk_job_task(self, state: BulkJobState, coro_factory: JobCallable) -> None:
        job_id = state.job_id

        async def wrapped() -> None:
            register_bulk_cancel(job_id)
            try:
                await coro_factory()
                if state.stop_requested:
                    state.status = SearchStatus.STOPPED
                elif state.status not in (SearchStatus.FAILED, SearchStatus.STOPPED, SearchStatus.PAUSED):
                    state.status = SearchStatus.COMPLETED
            except asyncio.CancelledError:
                if state.stop_requested:
                    state.status = SearchStatus.STOPPED
                else:
                    # Server reload or process shutdown — keep RUNNING so startup can recover.
                    state.status = SearchStatus.RUNNING
                    state.finished_at = None
                raise
            except Exception as exc:
                logger.exception("Bulk job %s failed", job_id)
                state.status = SearchStatus.FAILED
                state.error = str(exc) or repr(exc)
            finally:
                if state.status in (
                    SearchStatus.STOPPED,
                    SearchStatus.COMPLETED,
                    SearchStatus.FAILED,
                ):
                    if state.finished_at is None:
                        state.finished_at = datetime.now(timezone.utc)
                else:
                    state.finished_at = None
                state.pause_requested = False
                if state.status != SearchStatus.RUNNING:
                    state.current_city = None
                    state.current_category = None
                clear_bulk_cancel(job_id)
                from app.services.bulk_job_persistence import schedule_sync_bulk_job

                schedule_sync_bulk_job(state)

        state._task = asyncio.create_task(wrapped())

    def get_job(self, job_id: str) -> JobState | None:
        return self._jobs.get(job_id)

    def get_bulk_job(self, job_id: str) -> BulkJobState | None:
        return self._bulk_jobs.get(job_id)

    def get_active_bulk_job(self) -> BulkJobState | None:
        return next(
            (job for job in self._bulk_jobs.values() if job.status in _ACTIVE_BULK_STATUSES),
            None,
        )

    def get_running_bulk_job(self) -> BulkJobState | None:
        return self.get_active_bulk_job()

    def request_bulk_pause(self, job_id: str) -> BulkJobState:
        job = self._require_active_bulk_job(job_id)
        job.pause_requested = True
        job.status = SearchStatus.PAUSED
        return job

    def request_bulk_resume(self, job_id: str) -> BulkJobState:
        job = self._require_bulk_job(job_id)
        if job.status in _ACTIVE_BULK_STATUSES:
            job.pause_requested = False
            job.stop_requested = False
            job.status = SearchStatus.RUNNING
            job.finished_at = None
            register_bulk_cancel(job_id)
            return job
        if job.status == SearchStatus.STOPPED and job.completed_queries < job.total_queries:
            job.pause_requested = False
            job.stop_requested = False
            job.status = SearchStatus.RUNNING
            job.finished_at = None
            job.error = None
            register_bulk_cancel(job_id)
            return job
        raise ValueError(f"Bulk job {job_id} is not active")

    def request_bulk_stop(self, job_id: str) -> BulkJobState:
        job = self._require_bulk_job(job_id)
        if job.status == SearchStatus.STOPPED:
            return job
        if job.status not in _ACTIVE_BULK_STATUSES:
            raise ValueError(f"Bulk job {job_id} is not active")
        job.stop_requested = True
        job.pause_requested = False
        job.status = SearchStatus.STOPPED
        job.finished_at = datetime.now(timezone.utc)
        job.current_city = None
        job.current_category = None
        signal_bulk_cancel(job_id)
        return job

    def update_progress(self, job_id: str, *, found: int | None = None, saved: int | None = None) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        if found is not None:
            job.prospects_found = found
        if saved is not None:
            job.prospects_saved = saved

    def update_bulk_progress(
        self,
        job_id: str,
        *,
        found_delta: int = 0,
        saved_delta: int = 0,
        saved_with_website_delta: int = 0,
        saved_total_delta: int = 0,
        skipped_delta: int = 0,
        completed_queries: int | None = None,
        current_city: str | None = None,
        current_category: str | None = None,
        total_queries: int | None = None,
    ) -> None:
        job = self._bulk_jobs.get(job_id)
        if job is None:
            return
        job.prospects_found += found_delta
        job.prospects_saved += saved_delta
        job.prospects_saved_with_website += saved_with_website_delta
        job.prospects_saved_total += saved_total_delta
        job.prospects_skipped_duplicates += skipped_delta
        if completed_queries is not None:
            job.completed_queries = completed_queries
        if current_city is not None:
            job.current_city = current_city
        if current_category is not None:
            job.current_category = current_category
        if total_queries is not None:
            job.total_queries = total_queries

    def _require_bulk_job(self, job_id: str) -> BulkJobState:
        job = self.get_bulk_job(job_id)
        if job is None:
            raise ValueError(f"Bulk job {job_id} not found")
        return job

    def _require_active_bulk_job(self, job_id: str) -> BulkJobState:
        job = self._require_bulk_job(job_id)
        if job.status not in _ACTIVE_BULK_STATUSES:
            raise ValueError(f"Bulk job {job_id} is not active")
        return job


job_runner = JobRunner()
