from fauna import Client, fql


def test_client_tracks_last_txn_ts(a_collection):
    c = Client()
    assert c.get_last_transaction_time() is None
    c.query(fql('${col}.all', col=a_collection))
    assert c.get_last_transaction_time() is not None


def test_client_txn_ts_are_independent(client, a_collection):
    c = Client()
    c.query(fql('${col}.all', col=a_collection))
    assert client.get_last_transaction_time() is not None
    assert c.get_last_transaction_time() is not None
    assert client.get_last_transaction_time() != c.get_last_transaction_time()
