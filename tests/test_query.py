from typing import Mapping
import json

import httpx

from pytest_httpx import HTTPXMock

from fauna import Client, Header, HTTPXClient
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


    httpx_mock: HTTPXMock,
def test_query_with_opts():
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
            secret="secret",
            http_client = HTTPXClient(mockClient),

    res = c.query(

    def validate_headers(request: httpx.Request):
        assert request.headers[Header.Linearized] == str(linearized).lower()
        # being explicit to not figure out encoding a Mapping in the test
        assert request.headers[Header.Tags] == "hello=world&testing=foobar"
        assert request.headers[Header.TimeoutMs] == f"{query_timeout_ms}"
        assert request.headers[Header.Traceparent] == traceparent

        return httpx.Response(
            status_code=200,
            json={"url": str(request.url)},
            "not used, just sending to a mock client",
            QueryOptions(
                tags="hello=world",
    with httpx.Client() as mockClient:
        c = Client(http_client=HTTPXClient(mockClient))

                linearized=True,
            "not used, just sending to a mock client",
                query_timeout_ms=5000,
                traceparent=traceparent,
                max_contention_retries=max_contention_retries,
        ))
                traceparent=traceparent,
    as_json = json.loads(res.read().decode("utf-8"))
