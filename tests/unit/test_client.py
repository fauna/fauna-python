from datetime import timedelta
from typing import Dict, Mapping

import httpx
import pytest
import pytest_subtests
from pytest_httpx import HTTPXMock

import fauna
from fauna import Client, HTTPXClient, Header, fql
from fauna.client import QueryOptions
from fauna.errors import QueryCheckError, ProtocolError, QueryRuntimeError


def test_client_defaults(monkeypatch):
    monkeypatch.delenv("FAUNA_ENDPOINT")
    monkeypatch.delenv("FAUNA_SECRET")
    client = Client()

    assert client._endpoint == "https://db.fauna.com"
    assert client._auth.secret == ""
    assert client._query_timeout_ms is None
    assert client._session == fauna.global_http_client


def test_client_env_overrides(monkeypatch):
    ep = "my_fauna_endpoint"
    secret = "my_secret"
    monkeypatch.setenv("FAUNA_ENDPOINT", ep)
    monkeypatch.setenv("FAUNA_SECRET", secret)
    client = Client()

    assert client._endpoint == ep
    assert client._auth.secret == secret


def test_client_only_creates_one_global_http_client():
    fauna.global_http_client = None

    Client()
    http_client = fauna.global_http_client
    Client()

    assert fauna.global_http_client == http_client


def test_client_with_args():
    endpoint = "my-endpoint"
    secret = "my-secret"
    timeout = timedelta(seconds=900)
    linearized = True
    max_retries = 100
    track = False
    tags = {"tag_name": "tag_value"}
    http_client = HTTPXClient(httpx.Client())

    client = Client(
        endpoint=endpoint,
        secret=secret,
        query_timeout=timeout,
        linearized=linearized,
        max_contention_retries=max_retries,
        query_tags=tags,
        http_client=http_client,
    )

    assert client._auth.secret == secret
    assert client._endpoint == endpoint
    assert client._query_timeout_ms == 900000
    assert client._query_tags == tags
    assert client._session == http_client


def test_get_set_transaction_time():
    c = Client()
    assert c.get_last_txn_ts() is None

    c.set_last_txn_ts(123)
    assert c.get_last_txn_ts() == 123


def test_get_query_timeout():
    c = Client()
    assert c.get_query_timeout() is None

    c = Client(query_timeout=timedelta(minutes=1))
    assert c.get_query_timeout() == timedelta(minutes=1)


def test_query_options_set(
    httpx_mock: HTTPXMock,
    linearized: bool,
    query_timeout_ms: float,
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
            query_tags={"project": "teapot"},
        )

        res = c.query(
            fql("not used, just sending to a mock client"),
            opts=QueryOptions(
                query_tags=tags,
                linearized=linearized,
                query_timeout=timedelta(milliseconds=query_timeout_ms),
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
        with subtests.test("should not be set"):
            expected = None

            c = Client(
                http_client=HTTPXClient(mockClient),
                query_tags=None,
            )
            c.query(fql("not used, just sending to a mock client"))
        with subtests.test("should be set on client"):
            expected = "project=teapot"

            c = Client(
                http_client=HTTPXClient(mockClient),
                query_tags={"project": "teapot"},
            )
            c.query(fql("not used, just sending to a mock client"))
        with subtests.test("should be set on query"):
            expected = "silly=pants"

            c = Client(
                http_client=HTTPXClient(mockClient),
                query_tags=None,
            )
            c.query(
                fql("not used, just sending to a mock client"),
                QueryOptions(query_tags={"silly": "pants"}),
            )
        with subtests.test("should avoid conflicts"):
            expected = "project=kettle"

            c = Client(
                http_client=HTTPXClient(mockClient),
                query_tags={"project": "teapot"},
            )
            c.query(
                fql("not used, just sending to a mock client"),
                QueryOptions(query_tags={"project": "kettle"}),
            )


def test_client_headers(
    subtests: pytest_subtests.SubTests,
    httpx_mock: HTTPXMock,
):
    expected: Dict[str, str] = {}

    def validate_headers(request: httpx.Request):
        for header in expected:
            assert request.headers[header] == expected[header]

        return httpx.Response(
            status_code=200,
            json={"data": "mocked"},
        )

    httpx_mock.add_callback(validate_headers)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)

        with subtests.test("should allow for custom header on Client"):
            expected = {"happy": "fox"}
            c = Client(
                http_client=http_client,
                additional_headers=expected,
            )
            c.query(fql("just a mock"))

        with subtests.test("should allow custom header"):
            c = Client(http_client=http_client)
            expected = {"yellow": "submarine"}
            c.query(
                fql("just a mock"),
                QueryOptions(additional_headers=expected),
            )

        with subtests.test("Linearized should be set on Client"):
            c = Client(
                http_client=http_client,
                linearized=True,
            )
            expected = {Header.Linearized: "true"}
            c.query(fql("just a mock"))

        with subtests.test("Linearized should be set on Query"):
            expected = {Header.Linearized: "true"}
            c = Client(http_client=http_client)
            c.query(
                fql("just a mock"),
                QueryOptions(linearized=True),
            )

        with subtests.test("Max Contention Retries on Client"):
            count = 5

            c = Client(
                http_client=http_client,
                max_contention_retries=count,
            )

            expected = {Header.MaxContentionRetries: f"{count}"}
            c.query(fql("just a mock"))

        with subtests.test("Max Contention Retries on Query"):
            count = 5
            expected = {Header.MaxContentionRetries: f"{count}"}
            c = Client(http_client=http_client)
            c.query(
                fql("just a mock"),
                QueryOptions(max_contention_retries=count),
            )

        # doesn't make sense to be set on the Client
        with subtests.test("Should have a Traceparent"):
            traceparent = "moshi-moshi"
            expected = {Header.Traceparent: traceparent}
            c = Client(http_client=http_client)
            c.query(
                fql("just a mock"),
                QueryOptions(traceparent=traceparent),
            )


def test_error_query_check_error(subtests, httpx_mock: HTTPXMock):

    def callback(_: httpx.Request):
        return httpx.Response(
            status_code=400,
            json={
                "error": {
                    "code": "invalid_query",
                    "message": "did not jump"
                }
            },
        )

    httpx_mock.add_callback(callback)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)
        c = Client(http_client=http_client)
        with pytest.raises(QueryCheckError, match="did not jump"):
            c.query(fql("the quick brown fox"))


def test_error_query_runtime_error(subtests, httpx_mock: HTTPXMock):

    def callback(_: httpx.Request):
        return httpx.Response(
            status_code=400,
            json={"error": {
                "code": "anything",
                "message": "did not jump"
            }},
        )

    httpx_mock.add_callback(callback)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)
        c = Client(http_client=http_client)
        with pytest.raises(QueryRuntimeError, match="did not jump"):
            c.query(fql("the quick brown fox"))


def test_error_protocol_error_missing_error_key(subtests,
                                                httpx_mock: HTTPXMock):

    def callback(_: httpx.Request):
        return httpx.Response(
            status_code=400,
            json={"data": "jumped"},
        )

    httpx_mock.add_callback(callback)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)
        c = Client(http_client=http_client)
        err = "400: Unexpected response\nResponse is in an unknown format: \n{'data': 'jumped'}"
        with pytest.raises(ProtocolError, match=err):
            c.query(fql("the quick brown fox"))


def test_error_protocol_error_missing_error_code(subtests,
                                                 httpx_mock: HTTPXMock):

    def callback(_: httpx.Request):
        return httpx.Response(
            status_code=400,
            json={"error": {
                "message": "boo"
            }},
        )

    httpx_mock.add_callback(callback)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)
        c = Client(http_client=http_client)
        err = "400: Unexpected response\nResponse is in an unknown format: \n{'error': {'message': 'boo'}}"
        with pytest.raises(ProtocolError, match=err):
            c.query(fql("the quick brown fox"))


def test_error_protocol_error_missing_error_message(subtests,
                                                    httpx_mock: HTTPXMock):

    def callback(_: httpx.Request):
        return httpx.Response(
            status_code=400,
            json={"error": {
                "code": "boo"
            }},
        )

    httpx_mock.add_callback(callback)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)
        c = Client(http_client=http_client)
        err = "400: Unexpected response\nResponse is in an unknown format: \n{'error': {'code': 'boo'}}"
        with pytest.raises(ProtocolError, match=err):
            c.query(fql("the quick brown fox"))


def test_error_protocol_data_missing(subtests, httpx_mock: HTTPXMock):

    def callback(_: httpx.Request):
        return httpx.Response(
            status_code=200,
            json={},
        )

    httpx_mock.add_callback(callback)

    with httpx.Client() as mockClient:
        http_client = HTTPXClient(mockClient)
        c = Client(http_client=http_client)
        err = "200: Unexpected response\nResponse is in an unknown format: \n{}"
        with pytest.raises(ProtocolError, match=err):
            c.query(fql("the quick brown fox"))
