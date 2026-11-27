"""A Broker program: a Broker with its own web, talking to a separate Universe.
Start the Universe first, then:

    python -m spaceknowledge.app.broker_program broker-1

The name must be one of the brokers in settings.json. The Broker keeps its own
accounts and inventories in state/<name>/, reads the shared server key from
state/universe/, and serves clients over HTTP on its own web port (8400 for
broker-1, 8401 for broker-2 with the default settings). Players connect with
`python -m spaceknowledge.client.program --port <that port>` or a browser, and
administrators with `python -m spaceknowledge.client.admin_program --port <that
port>`. The administrator's one-time code is written to
state/<name>/mailbox/admin_mailbox.txt, which stands in for an email.
"""

import argparse
import time
from contextlib import ExitStack
from datetime import date
from pathlib import Path

from spaceknowledge.app.admin_service import AdminService
from spaceknowledge.app.front import Front
from spaceknowledge.app.game import Game
from spaceknowledge.app.keys import MissingKeyError, read_existing_key
from spaceknowledge.app.layout import SETTINGS_FILE, UNIVERSE_STATE_DIR, broker_state_dir
from spaceknowledge.app.paths import (
    ACCOUNTS_FILE, MAILBOX_FILE, PENDING_FILE, PLAYERS_FILE, SERVER_KEY_FILE,
)
from spaceknowledge.app.settings import SettingsError, is_valid_name, load_settings
from spaceknowledge.broker.broker import Broker
from spaceknowledge.broker.broker_server import BrokerServer
from spaceknowledge.broker.inventory_repository import CorruptStoreError, JsonInventoryRepository
from spaceknowledge.broker.pending_repository import CorruptPendingError, JsonPendingRepository
from spaceknowledge.broker.metrics import BrokerMetrics
from spaceknowledge.common.logfile import LOG_DIR, close_log, open_log
from spaceknowledge.common.refusal import Refusal
from spaceknowledge.broker_web.http_adapter import BrokerWebServer
from spaceknowledge.transport.server_auth import CorruptKeyError, ServerIdentity
from spaceknowledge.transport.socket_channel import SocketChannel
from spaceknowledge.users.account_repository import CorruptAccountsError, JsonAccountRepository
from spaceknowledge.users.accounts import AccountRegistry
from spaceknowledge.users.admin_gate import AdminGate
from spaceknowledge.users.credentials import DEFAULT_ITERATIONS
from spaceknowledge.users.one_time import FileMailbox, OneTimePasswords
from spaceknowledge.users.session_book import SessionBook

# Clients are on this machine for now. Listening on every address would be a
# deliberate decision, and needs TLS first.
WEB_HOST = "127.0.0.1"


def build_broker(
    state_dir: Path,
    key_file: Path,
    host: str,
    port: int,
    start: str,
    name: str,
    iterations: int = DEFAULT_ITERATIONS,
    timeout: float = 3.0,
    admins: tuple[str, ...] = ("root",),
) -> Game:
    """Start (or restart) one Broker whose world is at host:port.

    The key must already exist. Unfinished operations from an earlier run are
    sent again BEFORE the Broker thread starts, so this raises ConnectionError
    if the world cannot be reached while something is still pending. The Game
    carries an AdminService whose one-time codes go to state_dir/mailbox.
    """
    if not isinstance(state_dir, Path):
        raise TypeError(f"state_dir must be a Path, not {type(state_dir).__name__}")
    if not isinstance(key_file, Path):
        raise TypeError(f"key_file must be a Path, not {type(key_file).__name__}")
    if not is_valid_name(name):
        raise ValueError(f"{name!r} is not a valid Broker name")
    key = read_existing_key(key_file)
    accounts = AccountRegistry(JsonAccountRepository(state_dir / ACCOUNTS_FILE), iterations)
    codes = OneTimePasswords(admins, FileMailbox(state_dir / MAILBOX_FILE))
    metrics = BrokerMetrics()

    with ExitStack() as stack:
        channel = SocketChannel(host, port, ServerIdentity(name, key), timeout)
        stack.callback(channel.close)
        broker = Broker(channel, JsonInventoryRepository(state_dir / PLAYERS_FILE),
                        JsonPendingRepository(state_dir / PENDING_FILE))
        metrics.set_recovered(broker.recover())
        metrics.set_pending(broker.pending_count())

        broker_server = BrokerServer(broker, metrics=metrics)
        broker_server.start()
        stack.callback(broker_server.stop)  # runs first, then the channel closes

        front = Front(accounts, SessionBook(), broker_server, start)
        admin = AdminService(AdminGate(codes), accounts, broker_server, name)
        return Game(front, stack.pop_all(), admin)


class BrokerNode:
    """A running Broker and the web clients reach it through."""

    def __init__(self, game: Game, web: BrokerWebServer) -> None:
        if not isinstance(game, Game):
            raise TypeError(f"game must be a Game, not {type(game).__name__}")
        if not isinstance(web, BrokerWebServer):
            raise TypeError(f"web must be a BrokerWebServer, not {type(web).__name__}")
        self._game = game
        self._web = web

    @property
    def address(self) -> tuple[str, int]:
        """Where clients connect: the web, and nothing behind it."""
        return self._web.address

    def close(self) -> None:
        """Stop the web first, so no new request arrives, then the Broker.
        Harmless to call twice."""
        try:
            self._web.stop()
        finally:
            self._game.close()


def start_broker_node(
    state_dir: Path,
    key_file: Path,
    host: str,
    port: int,
    start: str,
    name: str,
    WEB_HOST: str = WEB_HOST,
    web_port: int = 0,
    iterations: int = DEFAULT_ITERATIONS,
    timeout: float = 3.0,
    admins: tuple[str, ...] = ("root",),
) -> BrokerNode:
    """A Broker plus its web. If the web cannot start (for example its port is
    taken), the Broker is stopped again and the error is raised. Port 0 lets
    the system pick a free port."""
    game = build_broker(state_dir, key_file, host, port, start, name, iterations, timeout, admins)
    web: BrokerWebServer | None = None
    try:
        web = BrokerWebServer(game.front, WEB_HOST, web_port, admin=game.admin)
        web.start()
    except BaseException:
        if web is not None:
            web.stop()
        game.close()
        raise
    return BrokerNode(game, web)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start a Broker and its web.")
    parser.add_argument("name", help="this Broker's name, one of the brokers in settings.json")
    args = parser.parse_args(argv)
    handler = open_log(LOG_DIR, date.today())
    try:
        try:
            settings = load_settings(SETTINGS_FILE)
            if args.name not in settings.brokers:
                raise SettingsError(f"{args.name} is not one of the brokers in settings.json")
            node = start_broker_node(
                broker_state_dir(args.name), UNIVERSE_STATE_DIR / SERVER_KEY_FILE,
                settings.universe_host, settings.universe_port, settings.start, args.name,
                WEB_HOST, settings.web_port(args.name), admins=settings.admins,
            )
        except (SettingsError, MissingKeyError, CorruptKeyError, CorruptStoreError,
                CorruptPendingError, CorruptAccountsError, OSError) as problem:
            print(Refusal(
                "start the Broker", str(problem),
                "check that the Universe is running, that the name is in settings.json, "
                "that its port is free, and that the files named above are intact",
            ).describe())
            return 1
        host, port = node.address
        print(f"{args.name} is ready. Clients connect to {host}:{port}.")
        print("Press Ctrl+C to stop it.")
        try:
            while True:
                time.sleep(1)  # a loop, because one long wait is not interruptible on Windows
        except KeyboardInterrupt:
            print("\nStopping.")
        finally:
            node.close()
        return 0
    finally:
        close_log(handler)


if __name__ == "__main__":
    raise SystemExit(main())