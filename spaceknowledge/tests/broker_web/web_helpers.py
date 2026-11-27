"""A running web in front of a small game, and a tiny HTTP caller for the tests."""

import http.client
import json

from spaceknowledge.broker_web.http_adapter import BrokerWebServer
from spaceknowledge.tests.app.helpers import a_game


def a_broker_web(test):
    """Returns (web, front, mailbox). Port 0: the system picks a free port."""
    front, admin, mailbox = a_game(test)
    web = BrokerWebServer(front, port=0, admin=admin)
    web.start()
    test.addCleanup(web.stop)
    return web, front, mailbox


def call(web, method, path, body=None, token=None, raw=None, headers=None):
    """Send one real HTTP request. Returns (status, parsed JSON or None, headers)."""
    host, port = web.address
    connection = http.client.HTTPConnection(host, port, timeout=5)
    sent = dict(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        sent.setdefault("Content-Type", "application/json")
    if token is not None:
        sent["Authorization"] = "Bearer " + token
    try:
        connection.request(method, path, body=data, headers=sent)
        response = connection.getresponse()
        payload = response.read()
        kind = response.getheader("Content-Type", "")
        parsed = json.loads(payload) if kind.startswith("application/json") else None
        return response.status, parsed, dict(response.getheaders())
    finally:
        connection.close()