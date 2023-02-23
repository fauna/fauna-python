from typing import Mapping

import httpx
import pytest
from pytest_httpx import HTTPXMock

from fauna import Client, Header, HTTPXClient
from fauna.client import QueryOptions, FaunaException


def test_query(subtests):
    c = Client()

    with subtests.test(msg="valid query"):
        res = c.query("Math.abs(-5.123e3)")

        assert res.data == float(5123.0)
        assert res.status_code == 200
        assert res.stats["compute_ops"] > 0
        assert res.traceparent != ""
        assert res.summary == ""
    with subtests.test(msg="with debug"):
        res = c.query('dbg("Hello, World")')

        assert res.status_code == 200
        assert res.summary != ""
    with subtests.test(msg="with error"):
        with pytest.raises(FaunaException) as e:
            c.query("I'm a little teapot")
        assert e.value.status_code == 400
        assert e.value.error_code == "invalid_query"
        assert e.value.error_message != ""
        assert e.value.summary != ""


def test_query_with_opts(
    httpx_mock: HTTPXMock,
    linearized: bool,
    query_timeout_ms: int,
    traceparent: str,
    tags: Mapping[str, str],
    max_contention_retries: int,
):

    def validate_headers(request: httpx.Request):
        assert request.headers[Header.Linearized] == str(linearized).lower()
        # being explicit to not figure out encoding a Mapping in the test
        assert request.headers[Header.Tags] == "hello=world&testing=foobar"
        assert request.headers[Header.TimeoutMs] == f"{query_timeout_ms}"
        assert request.headers[Header.Traceparent] == traceparent
        assert request.headers[
            Header.MaxContentionRetries] == f"{max_contention_retries}"

        return httpx.Response(
            status_code=200,
            json={"data": "mocked"},
        )

    httpx_mock.add_callback(validate_headers)

    with httpx.Client() as mockClient:
        c = Client(http_client=HTTPXClient(mockClient))

        res = c.query(
            "not used, just sending to a mock client",
            QueryOptions(
                tags=tags,
                linearized=linearized,
                query_timeout_ms=query_timeout_ms,
                traceparent=traceparent,
                max_contention_retries=max_contention_retries,
            ))

        assert res.status_code == 200
