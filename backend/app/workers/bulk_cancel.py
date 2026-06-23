import threading

_bulk_cancel_events: dict[str, threading.Event] = {}
_lock = threading.Lock()


def register_bulk_cancel(bulk_job_id: str) -> None:
    with _lock:
        _bulk_cancel_events[bulk_job_id] = threading.Event()


def signal_bulk_cancel(bulk_job_id: str) -> None:
    with _lock:
        event = _bulk_cancel_events.get(bulk_job_id)
    if event is not None:
        event.set()


def clear_bulk_cancel(bulk_job_id: str) -> None:
    with _lock:
        _bulk_cancel_events.pop(bulk_job_id, None)


def is_bulk_cancel_requested(bulk_job_id: str | None) -> bool:
    if bulk_job_id is None:
        return False
    with _lock:
        event = _bulk_cancel_events.get(bulk_job_id)
    return event is not None and event.is_set()
