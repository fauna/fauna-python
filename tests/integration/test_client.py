import pytest

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
