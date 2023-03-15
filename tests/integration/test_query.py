import pytest

from fauna import fql
from fauna.errors import QueryRuntimeError, ConstraintFailure
from fauna.response import Stat


def test_query(subtests, client):

    with subtests.test(msg="valid query"):
        res = client.query(fql("Math.abs(-5.123e3)"))

        assert res.status_code == 200
        assert res.data == float(5123.0)
        assert res.stats[Stat.ComputeOps] > 0
        assert res.traceparent != ""
        assert res.summary == ""

    with subtests.test(msg="with debug"):
        res = client.query(fql('dbg("Hello, World")'))

        assert res.status_code == 200
        assert res.summary != ""

    with subtests.test(msg="stats"):
        res = client.query(fql("Math.abs(-5.123e3)"))
        with subtests.test(msg="valid stat"):
            assert res.stats[Stat.ComputeOps] > 0
        with subtests.test(msg="invalid stat"):
            with pytest.raises(Exception) as e:
                assert res.stats["silly"] == 0
            assert e.type == KeyError
        with subtests.test(msg="manual stat"):
            # prove that we can use a plain string
            assert res.stats["read_ops"] == 0


def test_query_with_constraint_failure(client):
    with pytest.raises(QueryRuntimeError) as e:
        client.query(
            fql('Function.create({"name": "double", "body": "x => x * 2"})'))

    assert e.value.constraint_failures == [
        ConstraintFailure(message="The identifier `double` is reserved.",
                          name=None,
                          paths=[["name"]]),
    ]
    assert e.value.status_code == 400
    assert e.value.code == "constraint_failure"
    assert e.value.message == "Failed to create document in collection Function."
    assert len(e.value.summary) > 0
