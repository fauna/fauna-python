from io import StringIO

from faunadb.client_logger import json_logger
from faunadb.client import FaunaClient
from syrupy import SnapshotAssertion
from syrupy.filters import props


def test_logging(root_client, snapshot: SnapshotAssertion):
    logged = get_logged(root_client, lambda client: client.query("{x: 123}"))

    # data = StringIO(logged).read()
    assert logged == snapshot(exclude=props(
        "txn_time",
        "x-txn-time",
        "x-query-time",
        "traceparent",
        "latency",
    ))


def get_logged(root_client, client_action):
    logging_outputs = []
    client = root_client.new_session_client(
        observer=json_logger(logging_outputs.append))
    client_action(client)
    return logging_outputs[0]
