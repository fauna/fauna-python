from fauna.utils import LastTxnTs


def test_last_txn_time_initializes_with_none():
    t = LastTxnTs()
    assert t.time is None


def test_last_txn_time_cannot_regress():
    t = LastTxnTs()
    t.update_txn_time(10)
    t.update_txn_time(9)
    assert t.time == 10


def test_last_txn_time_can_advance():
    t = LastTxnTs()
    t.update_txn_time(10)
    t.update_txn_time(11)
    assert t.time == 11
