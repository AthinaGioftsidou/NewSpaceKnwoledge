"""REPOSITORY. The Broker's notebook: every operation that is in flight.

An operation is written here BEFORE it is sent to the Universe, and crossed
off only after its answer has been applied to players.json. So if the power
goes out while the torch is in flight, pending.json still says so. At start
the Broker compares this file with players.json:

    in pending.json AND in players.json's "settled" list
        the answer was already applied: just cross it off
    in pending.json only
        still in flight: lock the item again (flight state) and send the
        operation again with the SAME op_id, which the Universe recognises

The file is checked field by field when it is read, like every file.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from spaceknowledge.common.atomic_json import write_json_atomically
from spaceknowledge.common.messages import Request


class CorruptPendingError(ValueError):
    """A pending file that cannot be trusted, so it was not used."""


class PendingRepository(ABC):
    """What the Broker needs from its notebook: save the whole list, load it."""

    @abstractmethod
    def load(self) -> list[Request]:
        """The operations in flight, oldest first, or [] if there are none."""

    @abstractmethod
    def save(self, pending: list[Request]) -> None:
        """Replace the whole list with `pending`."""


def _checked(pending: list[Request]) -> list[Request]:
    """The list, if every entry is a Request and no op_id repeats. Raises
    otherwise, before anything is saved."""
    seen: set[str] = set()
    for request in pending:
        if not isinstance(request, Request):
            raise TypeError(f"pending must hold Requests, not {type(request).__name__}")
        if request.op_id in seen:
            raise ValueError(f"pending operation {request.op_id} appears twice")
        seen.add(request.op_id)
    return list(pending)  # Requests are read-only, so sharing them is safe


class InMemoryPendingRepository(PendingRepository):
    """Keeps the list in memory. For tests, and for a Broker with no file."""

    def __init__(self) -> None:
        self._pending: list[Request] = []

    def load(self) -> list[Request]:
        return list(self._pending)

    def save(self, pending: list[Request]) -> None:
        self._pending = _checked(pending)


class JsonPendingRepository(PendingRepository):
    """pending.json, written so it is never half written."""

    VERSION = 1

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise TypeError(f"path must be a Path, not {type(path).__name__}")
        self._path = path

    def load(self) -> list[Request]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as problem:
            raise self._corrupt(f"is not valid JSON ({problem})") from None
        if not isinstance(raw, dict) or raw.get("version") != self.VERSION:
            raise self._corrupt(f"is not a version {self.VERSION} pending file")
        operations = raw.get("pending")
        if not isinstance(operations, list):
            raise self._corrupt("has no pending list")
        seen: set[str] = set()
        return [self._check_request(body, seen) for body in operations]

    def save(self, pending: list[Request]) -> None:
        waiting = _checked(pending)
        write_json_atomically(
            self._path,
            {"version": self.VERSION, "pending": [self._encode(request) for request in waiting]},
        )

    @staticmethod
    def _encode(request: Request) -> dict[str, Any]:
        return {
            "op_id": request.op_id,
            "action": request.action,
            "player_id": request.player_id,
            "item_id": request.item_id,
            "amount": request.amount,
            "name": request.name,
        }

    def _corrupt(self, why: str) -> CorruptPendingError:
        return CorruptPendingError(f"{self._path.name} {why}")

    def _text(self, value: Any, what: str) -> str:
        if not isinstance(value, str) or not value:
            raise self._corrupt(f"has {what} that is not text")
        return value

    def _check_request(self, body: Any, seen: set[str]) -> Request:
        if not isinstance(body, dict):
            raise self._corrupt("has a bad pending operation")
        expected = {"op_id", "action", "player_id", "item_id", "amount", "name"}
        if set(body) != expected:
            raise self._corrupt("has a pending operation with missing or unexpected fields")
        op_id = self._text(body["op_id"], "a pending operation id")
        action = self._text(body["action"], f"an action for {op_id}")
        player_id = self._text(body["player_id"], f"a player for {op_id}")
        item_id = self._text(body["item_id"], f"an item for {op_id}")
        amount = body["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
            raise self._corrupt(f"has a bad amount for {op_id}")
        name = body["name"]
        if name is not None and (not isinstance(name, str) or not name):
            raise self._corrupt(f"has a bad name for {op_id}")
        if op_id in seen:
            raise self._corrupt(f"has {op_id} twice")
        seen.add(op_id)
        # Built only after every part is checked, so a bad file raises
        # CorruptPendingError and never a bare ValueError from Request.
        return Request(op_id, action, player_id, item_id, amount, name)