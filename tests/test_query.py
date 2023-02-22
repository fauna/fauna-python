import json

from fauna import Client
from fauna.client import QueryOptions


def test_query():
    c = Client(secret="secret")
    q = """let foo = 'bar'
    foo"""

    res = c.query(q)

    as_json = json.loads(res.read().decode("utf-8"))
    if "data" not in as_json:
        print(json.dumps(as_json, indent=2))

    assert as_json["data"] == 'bar'


def test_query_with_opts():
    c = Client(secret="secret")
    res = c.query(
        "Math.abs(-5.123e3)",
        QueryOptions(
            tags="hello=world",
            lineraized=True,
            query_timeout_ms=5000,
        ))
    # TODO: assert HTTP Client Request Headers contain expected values
    as_json = json.loads(res.read().decode("utf-8"))
    assert "error" not in as_json
