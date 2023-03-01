from typing import Mapping

import httpx
import pytest
import pytest_subtests
from pytest_httpx import HTTPXMock

from fauna import Client, Header, HTTPXClient, fql
from fauna.client import QueryOptions
from fauna.response import Stat


def test_query(subtests):
    c = Client()

    with subtests.test(msg="valid query"):
        res = c.query(fql("Math.abs(-5.123e3)"))

        assert res.status_code == 200
        assert res.data == float(5123.0)
        assert res.stat(Stat.ComputeOps) > 0
        assert res.traceparent != ""
        assert res.summary == ""

    with subtests.test(msg="with debug"):
        res = c.query(fql('dbg("Hello, World")'))

        assert res.status_code == 200
        assert res.summary != ""

    with subtests.test(msg="stats"):
        res = c.query(fql("Math.abs(-5.123e3)"))
        with subtests.test(msg="valid stat"):
            assert res.stat(Stat.ComputeOps) > 0
        with subtests.test(msg="invalid stat"):
            with pytest.raises(Exception) as e:
                assert res.stat("silly") == 0
            assert e.type == KeyError
        with subtests.test(msg="manual stat"):
            # prove that we can use a plain string
            assert res.stat("read_ops") == 0


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
        assert request.headers[Header.Tags] == \
            "project=teapot&hello=world&testing=foobar"
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
        c = Client(
            http_client=HTTPXClient(mockClient),
            tags={"project": "teapot"},
        )

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


def test_query_tags(
    subtests: pytest_subtests.SubTests,
    httpx_mock: HTTPXMock,
):
    expected = None

    def validate_tags(request: httpx.Request):
        if expected is not None:
            assert request.headers[Header.Tags] == expected
        else:
            with pytest.raises(KeyError):
                assert request.headers[Header.Tags] == ""

        return httpx.Response(
            status_code=200,
            json={"data": "mocked"},
        )

    httpx_mock.add_callback(validate_tags)

    with httpx.Client() as mockClient:
        c = Client(
            http_client=HTTPXClient(mockClient),
            tags=None,
        )

        with subtests.test("should be empty"):
            expected = None
            c.query(fql("not used, just sending to a mock client"))
        with subtests.test("should be set on client"):
            c.tags.update({"project": "teapot"})
            expected = "project=teapot"
            c.query(fql("not used, just sending to a mock client"))
        with subtests.test("should be set on query"):
            c.tags.clear()
            c.query(
                fql("not used, just sending to a mock client"),
                QueryOptions(query_tags={"project": "teapot"}),
            )
        with subtests.test("should avoid conflicts"):
            c.tags.update({"project": "teapot"})
            expected = "project=kettle"
            c.query(
                fql("not used, just sending to a mock client"),
                QueryOptions(query_tags={"project": "kettle"}),
            )
