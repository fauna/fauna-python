import pytest

from fauna import fql
from fauna.response import Stat


def test_query(subtests, client):

    with subtests.test(msg="valid query"):
        res = client.query(fql("Math.abs(-5.123e3)"))

        assert res.status_code == 200
        assert res.data == float(5123.0)
        assert res.stat(Stat.ComputeOps) > 0
        assert res.traceparent != ""
        assert res.summary == ""

    with subtests.test(msg="with debug"):
        res = client.query(fql('dbg("Hello, World")'))

        assert res.status_code == 200
        assert res.summary != ""

    with subtests.test(msg="stats"):
        res = client.query(fql("Math.abs(-5.123e3)"))
        with subtests.test(msg="valid stat"):
            assert res.stat(Stat.ComputeOps) > 0
        with subtests.test(msg="invalid stat"):
            with pytest.raises(Exception) as e:
                assert res.stat("silly") == 0
            assert e.type == KeyError
        with subtests.test(msg="manual stat"):
            # prove that we can use a plain string
            assert res.stat("read_ops") == 0
