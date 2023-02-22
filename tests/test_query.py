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
    c = Client(secret="secret")

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
            "Math.abs(-5.123e3)",
            QueryOptions(
            tags="hello=world",
    with httpx.Client() as mockClient:
        c = Client(http_client=HTTPXClient(mockClient))

            linearized=True,
            "not used, just sending to a mock client",
            query_timeout_ms=5000,
        ))
                traceparent=traceparent,
    as_json = json.loads(res.read().decode("utf-8"))
