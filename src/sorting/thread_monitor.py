
from time import perf_counter
from threading import current_thread


def create_event(start_time, kind, task, values=None):
    """Create a timestamped event for the thread activity monitor."""
    event = {
        "kind": kind,
        "thread": current_thread().name,
        "task": task,
        "at": round((perf_counter() - start_time) * 1000, 3)
    }

    if values is not None:
        event["values"] = values

    return event


def record_event(events, start_time, kind, task, values=None):
    """Append a thread activity event."""
    event = create_event(start_time, kind, task, values)
    events.append(event)
    return event

