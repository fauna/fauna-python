import pytest

from fauna import fql, Document
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


def test_advanced_composition(client, a_collection):
    test_email = "foo@fauna.com"
    index = {
        "indexes": {
            "byEmail": {
                "terms": [{
                    "field": "email"
                }],
                "values": [{
                    "field": "email"
                }]
            }
        }
    }
    client.query(
        fql("${col}.definition.update(${idx})", col=a_collection, idx=index))
    doc = client.query(
        fql("${col}.create(${doc})",
            col=a_collection,
            doc={
                "email": test_email,
                "alias": "bar"
            })).data

    def doc_by_email(email: str):
        return fql("${col}.byEmail(${email}).first()",
                   col=a_collection,
                   email=email)

    def update_doc_by_email(email: str, data: dict):
        q = """
let u = ${user}
u.update(${data})
"""
        return fql(q, user=doc_by_email(email), data=data)

    result = client.query(update_doc_by_email(test_email, {"alias": "baz"}))

    assert isinstance(result.data, Document)
    assert result.data["email"] == test_email
    assert result.data["alias"] == "baz"
    assert result.data.id == doc.id
    assert result.data.coll == doc.coll
    assert result.data.ts != doc.ts
