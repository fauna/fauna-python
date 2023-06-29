from datetime import timedelta
import pytest
from fauna.client.client import QueryOptions

from fauna.errors import ClientError

from fauna import fql
from fauna.client import Client


def test_client_tracks_last_txn_ts(a_collection):
    c = Client()
    assert c.get_last_txn_ts() is None
    c.query(fql('${col}.all', col=a_collection))
    assert c.get_last_txn_ts() is not None


def test_client_txn_ts_are_independent(client, a_collection):
    c = Client()
    c.query(fql('${col}.all', col=a_collection))
    assert client.get_last_txn_ts() is not None
    assert c.get_last_txn_ts() is not None
    assert client.get_last_txn_ts() != c.get_last_txn_ts()


def test_handle_invalid_json_response():
    err_msg = "Unable to decode response from endpoint https://dashboard.fauna.com/query/1. Check that your endpoint " \
              "is valid."
    with pytest.raises(ClientError, match=err_msg):
        c = Client(endpoint="https://dashboard.fauna.com/")
        c.query(fql("'foolery'"))


def test_fauna_accepts_query_timeout_header():
    c1 = Client(query_timeout=timedelta(seconds=5))
    c1.query(fql('"hello"'))

    c2 = Client()
    c2.query(fql('"hello"'), QueryOptions(query_timeout=timedelta(seconds=5)))
