import pytest

import fauna
from fauna import fql, QueryRuntimeError, QueryCheckError
from fauna.client import QueryOptions
from fauna.wire_protocol import QueryStat, ConstraintFailure


def test_query_smoke_test(subtests, client):
    with subtests.test(msg="valid query"):
        res = client.query(fql("Math.abs(-5.123e3)"))

        assert res.data == float(5123.0)
        assert res.stats[QueryStat.ComputeOps] > 0
        assert res.traceparent != ""
        assert res.summary == ""

    with subtests.test(msg="with debug"):
        res = client.query(fql('dbg("Hello, World")'))

        assert res.summary != ""


def test_query_with_all_stats(client, a_collection):
    res = client.query(fql("${col}.create({})", col=a_collection))
    for stat in QueryStat:
        assert res.stats[stat] >= 0


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
    qi = e.value.query_info
    assert qi is not None and len(qi.summary) > 0


def test_bad_request(client):
    with pytest.raises(QueryCheckError) as e:
        client.query(fql("{ bad: 'request']"))

    assert e.value.code == "invalid_query"
    assert len(e.value.message) > 0
    assert e.value.query_info is not None
    assert len(e.value.query_info.stats) > 0
    assert len(e.value.query_info.summary) > 0


@pytest.mark.skip(reason="not currently supported by core")
def test_traceparent_echos(client):
    tp = "00-3afc487855c5de345d8752f464add590-5a0bef45234dc1b6-00"
    res = client.query(fql("'Hello'"), QueryOptions(traceparent=tp))
    assert res.traceparent == tp


def test_query_tags_echo():
    client_qt = {"env": "valhalla"}
    qt = {"version": "thor"}
    client = fauna.Client(query_tags=client_qt)
    opts = QueryOptions(query_tags=qt)
    res = client.query(fql("42"), opts)
    assert res.query_tags == client_qt | qt


def test_handles_typecheck_format():
    client = fauna.Client(typecheck=True)
    res = client.query(fql("""
if (true) { 
  42
} else {
  41
}"""))
    assert res.static_type == "42 | 41"
