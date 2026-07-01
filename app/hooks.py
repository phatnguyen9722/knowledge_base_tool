"""Minimal plugin event system.

Register handlers with the `@on(event)` decorator; fire them with `emit`.
PostManager emits `on_post_created` / `on_post_updated` / `on_post_deleted`.
Handler exceptions are swallowed so a buggy plugin can't break a save.
"""

from __future__ import annotations

from typing import Callable

EVENTS = ("on_post_created", "on_post_updated", "on_post_deleted")

_handlers: dict[str, list[Callable]] = {e: [] for e in EVENTS}


def on(event: str):
    """Decorator: register a handler for an event. e.g. @on('on_post_created')."""
    if event not in _handlers:
        raise ValueError(f"Unknown event: {event!r}. Known: {', '.join(EVENTS)}")

    def decorator(fn: Callable) -> Callable:
        _handlers[event].append(fn)
        return fn

    return decorator


def emit(event: str, payload) -> None:
    """Fire all handlers for `event`. Handler errors are isolated."""
    for fn in _handlers.get(event, []):
        try:
            fn(payload)
        except Exception:
            # A misbehaving plugin must not break core CRUD.
            pass


def clear(event: str | None = None) -> None:
    """Remove handlers (all, or for one event). Mainly for tests."""
    if event is None:
        for e in _handlers:
            _handlers[e].clear()
    else:
        _handlers.get(event, []).clear()
