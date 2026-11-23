"""Builds a small running game for the app tests: a Universe, a Broker thread,
accounts and an admin gate. Everything in memory, nothing on disk."""

from spaceknowledge.app.admin_service import AdminService
from spaceknowledge.app.front import Front
from spaceknowledge.broker.broker import Broker
from spaceknowledge.broker.broker_server import BrokerServer
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.channel import InMemoryChannel
from spaceknowledge.users.accounts import AccountRegistry
from spaceknowledge.users.admin_gate import AdminGate
from spaceknowledge.users.one_time import InMemoryMailbox, OneTimePasswords
from spaceknowledge.users.session_book import SessionBook

PASSWORD = "correct horse"


def a_game(test):
    """Returns (front, admin, mailbox). Stops the Broker thread when the test ends."""
    server = BrokerServer(Broker(InMemoryChannel(a_universe())))
    server.start()
    test.addCleanup(server.stop)
    accounts = AccountRegistry(iterations=1)          # fast hashing, for tests only
    front = Front(accounts, SessionBook(), server, "earth")
    mailbox = InMemoryMailbox()
    admin = AdminService(AdminGate(OneTimePasswords(["root"], mailbox)), accounts, server, "broker-1")
    return front, admin, mailbox