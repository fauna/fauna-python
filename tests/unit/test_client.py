from datetime import timedelta
from typing import Mapping

import httpx
import pytest_subtests
from pytest_httpx import HTTPXMock

import fauna
from fauna import Client, HTTPXClient, Header, fql
from fauna.client import QueryOptions


def test_client_defaults(monkeypatch):
    monkeypatch.delenv("FAUNA_ENDPOINT")
    monkeypatch.delenv("FAUNA_SECRET")
    client = Client()

    assert client.max_contention_retries is None
    assert client.linearized is None
    assert client.endpoint == "https://db.fauna.com"
    assert client._auth.secret == ""
    assert client.track_last_transaction_time is True
    assert client._query_timeout_ms is None
    assert client.session == fauna.global_http_client


def test_client_env_overrides(monkeypatch):
    ep = "my_fauna_endpoint"
    secret = "my_secret"
    monkeypatch.setenv("FAUNA_ENDPOINT", ep)
    monkeypatch.setenv("FAUNA_SECRET", secret)
    client = Client()

    assert client.endpoint == ep
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
        track_last_transaction_time=track,
        tags=tags,
        http_client=http_client,
    )

    assert client._auth.secret == secret
    assert client.endpoint == endpoint
    assert client._query_timeout_ms == 900000
    assert client.linearized == linearized
    assert client.max_contention_retries == max_retries
    assert client.track_last_transaction_time == track
    assert client.tags == tags
    assert client.session == http_client


def test_get_set_transaction_time():
    c = Client()
    assert c.get_last_transaction_time() is None

    c.set_last_transaction_time(123)
    assert c.get_last_transaction_time() == 123


def test_get_query_timeout():
    c = Client()
    assert c.get_query_timeout() is None

    c = Client(query_timeout=timedelta(minutes=1))
    assert c.get_query_timeout() == timedelta(minutes=1)


def test_client_headers(
    subtests: pytest_subtests.SubTests,
    httpx_mock: HTTPXMock,
):
    expected: Mapping[str, str] = {}

    def validate_headers(request: httpx.Request):
        for header in expected:
            assert request.headers[header] == expected[header]

        return httpx.Response(
            status_code=200,
            json={"data": "mocked"},
        )

    httpx_mock.add_callback(validate_headers)

    with httpx.Client() as mockClient:
        c = Client(http_client=HTTPXClient(mockClient))

        with subtests.test("should allow custom header"):
            expected = {"yellow": "submarine"}
            c.headers.update(expected)
            c.query(fql("just a mock"))

        with subtests.test("Linearized should be set on Client"):
            c.linearized = True
            expected = {Header.Linearized: "true"}
            c.query(fql("just a mock"))

        with subtests.test("Linearized should be set on Query"):
            expected = {Header.Linearized: "true"}
            c.query(
                fql("just a mock"),
                QueryOptions(linearized=True),
            )

        with subtests.test("Max Contention Retries on Client"):
            c.max_contention_retries = 5
            expected = {Header.MaxContentionRetries: "5"}
            c.query(fql("just a mock"))

        with subtests.test("Max Contention Retries on Query"):
            expected = {Header.MaxContentionRetries: "5"}
            c.query(
                fql("just a mock"),
                QueryOptions(max_contention_retries=5),
            )

        # doesn't make sense to be set on the Client
        with subtests.test("Should have a Traceparent"):
            expected = {Header.Traceparent: "moshi-moshi"}
            c.query(
                fql("just a mock"),
                QueryOptions(traceparent="moshi-moshi"),
            )
