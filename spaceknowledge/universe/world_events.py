"""OBSERVER. The Universe tells whoever is watching what players do.

The Universe is the SUBJECT: it keeps a list of observers and calls `notify`
on each of them when a player drops or picks up an item. It does not know
what an observer does with the news.

Two observers exist:
    EventFeed     keeps the newest events, so the Brokers can ask for them
                  and show them to the other players in the same place
    EventLogger   writes every event to the log

Events are not saved: they are news, not state. After a restart the feed
starts empty.
"""

import logging
from abc import ABC, abstractmethod
from collections import deque

from spaceknowledge.common.messages import WorldEvent

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# How many events the feed keeps. Older ones are forgotten.
DEFAULT_KEEP = 200

# The most events one question about the news is answered with.
MAX_EVENTS_PER_ANSWER = 20


class WorldObserver(ABC):
    """Anything that wants to hear about what players do in the world."""

    @abstractmethod
    def notify(self, event: WorldEvent) -> None:
        """Called by the Universe, once per event, in the order they happen."""


class EventFeed(WorldObserver):
    """Keeps the newest events, and answers "what happened here since N?"."""

    def __init__(self, keep: int = DEFAULT_KEEP) -> None:
        if isinstance(keep, bool) or not isinstance(keep, int):
            raise TypeError(f"keep must be an int, not {type(keep).__name__}")
        if keep < 1:
            raise ValueError("keep must be at least 1")
        self._events: deque[WorldEvent] = deque(maxlen=keep)

    def notify(self, event: WorldEvent) -> None:
        if not isinstance(event, WorldEvent):
            raise TypeError(f"event must be a WorldEvent, not {type(event).__name__}")
        self._events.append(event)

    def since(self, seq: int, place: str, viewer: str) -> tuple[WorldEvent, ...]:
        """The events in `place` numbered after `seq`, except the viewer's own,
        oldest first and at most MAX_EVENTS_PER_ANSWER of the newest."""
        seen = [event for event in self._events
                if event.seq > seq and event.place == place and event.player_id != viewer]
        return tuple(seen[-MAX_EVENTS_PER_ANSWER:])

    def count(self) -> int:
        """How many events are kept."""
        return len(self._events)


class EventLogger(WorldObserver):
    """Writes every event to the log, so the administrator can read what happened."""

    def notify(self, event: WorldEvent) -> None:
        log.info("event %d in %s: %s", event.seq, event.place, event.describe())