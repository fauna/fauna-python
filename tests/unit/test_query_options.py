from typing import Mapping

import httpx
import pytest
from pytest_httpx import HTTPXMock

from fauna import Client, Header, HTTPXClient, fql
from fauna.client import QueryOptions


def test_query_options_default(httpx_mock: HTTPXMock, ):

    def validate_headers_empty(request: httpx.Request):
        """
        Validate none of the associated Headers should be set on the request
        """
        with pytest.raises(KeyError):
            assert request.headers[Header.Linearized] is None
        with pytest.raises(KeyError):
            assert request.headers[Header.Tags] is None
        with pytest.raises(KeyError):
            assert request.headers[Header.TimeoutMs] is None
        with pytest.raises(KeyError):
            assert request.headers[Header.Traceparent] is None
        with pytest.raises(KeyError):
            assert request.headers[Header.MaxContentionRetries] is None

        return httpx.Response(
            status_code=200,
            json={"data": "mocked, default"},
        )

    httpx_mock.add_callback(validate_headers_empty)

    with httpx.Client() as mockClient:
        c = Client(http_client=HTTPXClient(mockClient))

        res = c.query(fql("not used, just sending to a mock client"))

        assert res.status_code == 200


def test_query_options_set(
    httpx_mock: HTTPXMock,
    linearized: bool,
    query_timeout_ms: int,
    traceparent: str,
    tags: Mapping[str, str],
    max_contention_retries: int,
):

    def validate_headers(request: httpx.Request):
        """
        Validate each of the associated Headers are set on the request
        """
        assert request.headers[Header.Linearized] == str(linearized).lower()
        # being explicit to not figure out encoding a Mapping in the test
        assert request.headers[Header.Tags] == "hello=world&testing=foobar"
        assert request.headers[Header.TimeoutMs] == f"{query_timeout_ms}"
        assert request.headers[Header.Traceparent] == traceparent
        assert request.headers[Header.MaxContentionRetries] \
            == f"{max_contention_retries}"

        return httpx.Response(
            status_code=200,
            json={"data": "mocked"},
        )

    httpx_mock.add_callback(validate_headers)

    with httpx.Client() as mockClient:
        c = Client(http_client=HTTPXClient(mockClient))

        res = c.query(
            fql("not used, just sending to a mock client"),
            opts=QueryOptions(
                query_tags=tags,
                linearized=linearized,
                query_timeout_ms=query_timeout_ms,
                traceparent=traceparent,
                max_contention_retries=max_contention_retries,
            ),
        )

        assert res.status_code == 200
