"""The two messages that cross between the Broker and the Universe."""

from dataclasses import dataclass

from spaceknowledge.common.refusal import Refusal

# What a WorldEvent can report, and how it is told to the other players.
EVENT_VERBS = {"drop": "dropped", "pick": "picked up"}


class Request:
    """What the Broker asks the Universe to do. Read-only once made."""

    def __init__(
        self,
        op_id: str,
        action: str,
        player_id: str,
        item_id: str,
        amount: int = 1,
        name: str | None = None,
    ) -> None:
        if not op_id:
            raise ValueError("op_id must not be empty")
        if not action:
            raise ValueError("action must not be empty")
        if not player_id:
            raise ValueError("player_id must not be empty")
        if not item_id:
            raise ValueError("item_id must not be empty")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise TypeError(f"amount must be an int, not {type(amount).__name__}")
        if amount < 1:
            raise ValueError("amount must be at least 1")
        if name is not None and (not isinstance(name, str) or not name):
            raise ValueError("name must be a non-empty string, or left out")
        self._op_id = op_id
        self._action = action
        self._player_id = player_id
        self._item_id = item_id
        self._amount = amount
        self._name = name

    @property
    def op_id(self) -> str:
        return self._op_id

    @property
    def action(self) -> str:
        return self._action

    @property
    def player_id(self) -> str:
        return self._player_id

    @property
    def item_id(self) -> str:
        return self._item_id

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def name(self) -> str | None:
        """The display name, if the sender gave one."""
        return self._name

    @property
    def display_name(self) -> str:
        """The name to show: the given one, or the id when none was given."""
        return self._name if self._name is not None else self._item_id

@dataclass(frozen=True)
class ItemInfo:
    """Plain data about one item, so objects never cross between the servers.
    Read-only."""

    item_id: str
    name: str
    description: str

    def __post_init__(self) -> None:
        for label, value in (("item_id", self.item_id), ("name", self.name),
                             ("description", self.description)):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{label} must not be empty")

@dataclass(frozen=True)
class WorldEvent:
    """Something one player did that the others in the same place can see.
    Plain data, numbered in the order it happened. Read-only."""

    seq: int
    place: str
    player_id: str
    action: str
    item_name: str

    def __post_init__(self) -> None:
        if isinstance(self.seq, bool) or not isinstance(self.seq, int) or self.seq < 1:
            raise ValueError("seq must be a whole number of at least 1")
        for label, value in (("place", self.place), ("player_id", self.player_id),
                             ("item_name", self.item_name)):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{label} must not be empty")
        if self.action not in EVENT_VERBS:
            raise ValueError(f"action must be one of: {', '.join(EVENT_VERBS)}")

    def describe(self) -> str:
        """The sentence the other players see, e.g. "ada dropped a torch"."""
        return f"{self.player_id} {EVENT_VERBS[self.action]} a {self.item_name}"


@dataclass(frozen=True)
class News:
    """The answer to "what happened here since event N?": the events, and the
    newest event number anywhere, so the asker can move its counter on even
    when nothing happened where it is. Read-only."""

    events: tuple[WorldEvent, ...]
    latest: int

    def __post_init__(self) -> None:
        if not isinstance(self.events, tuple) or not all(
            isinstance(e, WorldEvent) for e in self.events
        ):
            raise TypeError("events must be a tuple of WorldEvent")
        if isinstance(self.latest, bool) or not isinstance(self.latest, int) or self.latest < 0:
            raise ValueError("latest must be a whole number, 0 or more")


class Response:
    """The Universe's answer: OK (with optional item data or news), or a Refusal.
    `events` and `latest` are used only by the answer to "news"."""

    def __init__(
        self,
        op_id: str,
        refusal: Refusal | None = None,
        items: tuple[ItemInfo, ...] = (),
        events: tuple[WorldEvent, ...] = (),
        latest: int = 0,
    ) -> None:
        if not op_id:
            raise ValueError("op_id must not be empty")
        if refusal is not None and not isinstance(refusal, Refusal):
            raise TypeError(f"refusal must be a Refusal, not {type(refusal).__name__}")
        if not isinstance(items, tuple) or not all(isinstance(i, ItemInfo) for i in items):
            raise TypeError("items must be a tuple of ItemInfo")
        if not isinstance(events, tuple) or not all(isinstance(e, WorldEvent) for e in events):
            raise TypeError("events must be a tuple of WorldEvent")
        if isinstance(latest, bool) or not isinstance(latest, int) or latest < 0:
            raise ValueError("latest must be a whole number, 0 or more")
        if refusal is not None and (items or events or latest):
            raise ValueError("a refusal carries no items and no news")
        self._op_id = op_id
        self._refusal = refusal
        self._items = items
        self._events = events
        self._latest = latest

    @property
    def op_id(self) -> str:
        return self._op_id

    @property
    def ok(self) -> bool:
        return self._refusal is None

    @property
    def refusal(self) -> Refusal | None:
        return self._refusal

    @property
    def items(self) -> tuple[ItemInfo, ...]:
        return self._items

    @property
    def events(self) -> tuple[WorldEvent, ...]:
        return self._events

    @property
    def latest(self) -> int:
        """The newest event number the Universe has given out (news only)."""
        return self._latest