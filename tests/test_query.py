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
    linearized: bool = True
    tags: str = "hello=world"
    query_timeout_ms: int = 5000
    traceparent: str = "happy-little-fox"
    max_contention_retries: int = 5

    def validate_headers(request: httpx.Request):
        assert request.headers[Header.Linearized] == str(linearized).lower()
        assert request.headers[Header.Tags] == tags
        assert request.headers[Header.TimeoutMs] == f"{query_timeout_ms}"
        assert request.headers[Header.Traceparent] == traceparent
        assert request.headers[Header.MaxContentionRetries] == f"{max_contention_retries}"

        return httpx.Response(
            status_code=200, json={"url": str(request.url)},
        )

    httpx_mock.add_callback(validate_headers)


    with httpx.Client() as mockClient:
        c = Client(http_client = HTTPXClient(mockClient))

        res = c.query(
            "not used, just sending to a mock client",
            QueryOptions(
                tags=tags,
                linearized=linearized,
                query_timeout_ms=query_timeout_ms,
                traceparent=traceparent,
                max_contention_retries=max_contention_retries,
            ))

        assert res.status_code() == 200
