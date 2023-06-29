from datetime import timedelta
import json
from types import SimpleNamespace

import pytest

from fauna import fql, Page, NullDocument
from fauna.client import Client, QueryOptions
from fauna.errors import QueryCheckError, QueryRuntimeError, AbortError, ClientError, QueryTimeoutError
from fauna.encoding import ConstraintFailure


def test_query_smoke_test(subtests, client):
    with subtests.test(msg="valid query"):
        res = client.query(fql("Math.abs(-5.123e3)"))

        assert res.data == float(5123.0)
        assert res.stats.compute_ops > 0
        assert res.traceparent != ""
        assert res.summary == ""

    with subtests.test(msg="with debug"):
        res = client.query(fql('dbg("Hello, World")'))

        assert res.summary != ""


def test_query_with_all_stats(client, a_collection):
    res = client.query(fql("${col}.create({})", col=a_collection))
    doc_id = res.data.id
    res = client.query(
        fql("${col}.create({})\n${col}.byId(${id})",
            col=a_collection,
            id=doc_id))
    assert res.stats.compute_ops > 0
    assert res.stats.read_ops > 0
    assert res.stats.write_ops > 0
    assert res.stats.storage_bytes_read > 0
    assert res.stats.storage_bytes_write > 0
    assert res.stats.query_time_ms > 0
    assert res.stats.contention_retries == 0


def test_query_with_constraint_failure(client):
    with pytest.raises(QueryRuntimeError) as e:
        client.query(
            fql('Function.create({"name": "false", "body": "_ => false"})'))

    assert e.value.constraint_failures == [
        ConstraintFailure(
            message="The identifier `false` is reserved.",
            name=None,
            paths=[["name"]],
        ),
    ]
    assert e.value.status_code == 400
    assert e.value.code == "constraint_failure"
    assert e.value.message == "Failed to create document in collection Function."
    assert len(e.value.summary) > 0


def test_query_page(client, a_collection):
    for n in range(100):
        client.query(fql("${col}.create({ n: ${n} })", col=a_collection, n=n))

    res = client.query(fql("${col}.all().map(x => x.n)", col=a_collection))
    p: Page = res.data
    assert p.data is not None and len(p.data) < 100
    assert p.after is not None


def test_bad_request(client):
    with pytest.raises(QueryCheckError) as e:
        client.query(fql("{ bad: 'request']"))

    assert e.value.code == "invalid_query"
    assert len(e.value.message) > 0
    assert len(e.value.summary) > 0

    stats = e.value.stats
    assert stats is not None
    assert stats.query_time_ms > 0


def test_abort(client):
    with pytest.raises(AbortError) as e:
        client.query(fql("abort({'foo': 123})"))

    ae: AbortError = e.value
    assert ae.abort == {"foo": 123}
    assert ae.code == "abort"
    assert ae.status_code == 400
    assert ae.stats.compute_ops == 1


@pytest.mark.skip(reason="not currently supported by core")
def test_traceparent_echos(client):
    tp = "00-3afc487855c5de345d8752f464add590-5a0bef45234dc1b6-00"
    res = client.query(fql("'Hello'"), QueryOptions(traceparent=tp))
    assert res.traceparent == tp


def test_query_tags_echo():
    client_qt = {"env": "valhalla"}
    qt = {"version": "thor"}
    client = Client(query_tags=client_qt)
    opts = QueryOptions(query_tags=qt)
    res = client.query(fql("42"), opts)
    assert res.query_tags == client_qt | qt


def test_handles_typecheck_format():
    client = Client(typecheck=True)
    res = client.query(fql("""
if (true) {
  42
} else {
  41
}"""))
    assert res.static_type == "42 | 41"


def test_fails_on_encoding_error(client):
    body = '{"orderProducts": {}}'
    test = json.loads(body, object_hook=lambda d: SimpleNamespace(**d))
    with pytest.raises(ClientError, match="Failed to encode Query"):
        client.query(fql("${prods}", prods=test.orderProducts))


def test_null_doc(client, a_collection):
    r = client.query(fql("${coll}.byId('123')", coll=a_collection))
    assert isinstance(r.data, NullDocument)
    assert r.data.cause == "not found"


def test_query_timeout(client, a_collection):
    with pytest.raises(QueryTimeoutError):
        client.query(fql("${coll}.byId('123')", coll=a_collection),
                     QueryOptions(query_timeout=timedelta(milliseconds=1)))
