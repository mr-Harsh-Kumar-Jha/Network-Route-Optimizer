"""
Simple in-process pub/sub: observers subscribe to event classes and are
notified synchronously when those events are published.

Module-level singleton pattern — setup_event_bus() is called once at startup,
get_event_bus() is called from services at request time.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ── Domain Events ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RouteComputedEvent:
    """
    Published whenever a shortest-path query is executed (success or failure).
    Observers decide how to react based on the `success` flag.
    """
    source: str
    destination: str
    path: list[str]
    total_latency: float | None
    success: bool
    algorithm_used: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ── Event Bus ─────────────────────────────────────────────────────────────────

class EventBus:
    """
    Synchronous pub/sub event bus.

    Observer failures are caught and logged — they must never crash
    the main request pipeline.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: Any) -> None:
        for handler in self._subscribers.get(type(event), []):
            try:
                handler(event)
            except Exception as exc:
                logger.error(
                    "EventBus: observer %s failed for %s: %s",
                    handler, type(event).__name__, exc, exc_info=True,
                )


# ── Module-level singleton ────────────────────────────────────────────────────

_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the application-level EventBus (set up at startup)."""
    if _bus is None:
        raise RuntimeError("EventBus not initialized. Call setup_event_bus() in lifespan.")
    return _bus


def setup_event_bus(session_factory) -> EventBus:
    """
    Initialize the EventBus with all registered observers.
    Called once during application startup (lifespan).
    """
    global _bus
    from app.network_optimizer.events.observers import AnalyticsObserver, HistoryObserver, LoggingObserver

    _bus = EventBus()
    _bus.subscribe(RouteComputedEvent, HistoryObserver(session_factory))
    _bus.subscribe(RouteComputedEvent, AnalyticsObserver())
    _bus.subscribe(RouteComputedEvent, LoggingObserver())
    return _bus
