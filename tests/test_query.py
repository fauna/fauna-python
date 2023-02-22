import json

import httpx

from pytest_httpx import HTTPXMock
from fauna import Client, Header, HTTPXClient
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


def test_query_with_opts(httpx_mock: HTTPXMock):
    def custom_response(request: httpx.Request):
        assert request.headers[Header.Linearized] == "true"
        assert request.headers[Header.Tags] == "hello=world"
        assert request.headers[Header.TimeoutMs] == "5000"

        return httpx.Response(
            status_code=200, json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response)


    with httpx.Client() as mockClient:
        c = Client(
            secret="secret",
            http_client = HTTPXClient(mockClient),
        )

        res = c.query(
            "Math.abs(-5.123e3)",
            QueryOptions(
                tags="hello=world",
                linearized=True,
                query_timeout_ms=5000,
            ))

        assert res.status_code() == 200
