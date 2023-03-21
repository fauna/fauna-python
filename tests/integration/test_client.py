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
