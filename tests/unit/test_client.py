from datetime import timedelta
from typing import Dict

import httpx
import pytest
import pytest_subtests
from pytest_httpx import HTTPXMock, IteratorStream

import fauna
from fauna import fql
from fauna.client import Client, Header, QueryOptions, Endpoints, StreamOptions
from fauna.errors import QueryCheckError, ProtocolError, QueryRuntimeError, NetworkError, AbortError
from fauna.http import HTTPXClient
from fauna.query import EventSource


def test_client_defaults(monkeypatch):
  monkeypatch.delenv("FAUNA_ENDPOINT")
  monkeypatch.delenv("FAUNA_SECRET")
  client = Client()

  assert client._endpoint == "https://db.fauna.com"
  assert client._auth.secret == ""
  assert client._query_timeout_ms is not None
  assert client._session == fauna.global_http_client


def test_client_env_overrides(monkeypatch):
  ep = "my_fauna_endpoint"
  secret = "my_secret"
  monkeypatch.setenv("FAUNA_ENDPOINT", ep)
  monkeypatch.setenv("FAUNA_SECRET", secret)
  client = Client()

  assert client._endpoint == ep
  assert client._auth.secret == secret


def test_client_strips_endpoint_trailing_slash(monkeypatch, subtests):

  with subtests.test(msg="trailing slash on env var"):
    ep = "https://db.fauna.com/"
    secret = "my_secret"
    monkeypatch.setenv("FAUNA_ENDPOINT", ep)
    monkeypatch.setenv("FAUNA_SECRET", secret)
    client = Client()

    assert client._endpoint == Endpoints.Default
    assert client._auth.secret == secret

  with subtests.test(msg="trailing slash on param"):
    ep = "http://localhost:8443/"
    secret = "secret"
    client = Client(endpoint=ep, secret=secret)

    assert client._endpoint == Endpoints.Local
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
  tags = {"tag_name": "tag_value"}
  typecheck = True
  additional_headers = {"foo": "bar"}

  http_client = HTTPXClient(httpx.Client())

  client = Client(
      endpoint=endpoint,
      secret=secret,
      query_timeout=timeout,
      linearized=linearized,
      max_contention_retries=max_retries,
      query_tags=tags,
      http_client=http_client,
      typecheck=typecheck,
      additional_headers=additional_headers,
  )

  assert client._auth.secret == secret
  assert client._endpoint == endpoint
  assert client._query_timeout_ms == 900000
  assert client._query_tags == tags
  assert client._session == http_client
  assert client._headers[Header.Typecheck] == "true"
  assert client._headers[Header.Linearized] == "true"
  assert client._headers[Header.MaxContentionRetries] == "100"
  assert client._headers["foo"] == "bar"


def test_get_set_transaction_time():
  c = Client()
  assert c.get_last_txn_ts() is None

  c.set_last_txn_ts(123)
  assert c.get_last_txn_ts() == 123


def test_get_query_timeout():
  c = Client(query_timeout=None)
  assert c.get_query_timeout() is None

  c = Client(query_timeout=timedelta(minutes=1))
  assert c.get_query_timeout() == timedelta(minutes=1)


def test_query_options_set(httpx_mock: HTTPXMock):

  typecheck = True
  linearized = True
  query_timeout_ms = 5000
  traceparent = "happy-little-fox"
  max_contention_retries = 5
  tags = {
      "hello": "world",
      "testing": "foobar",
  }
  additional_headers = {"additional": "header"}

  def validate_headers(request: httpx.Request):
    """
        Validate each of the associated Headers are set on the request
        """
    assert request.headers[Header.Linearized] == str(linearized).lower()
    assert request.headers[Header.QueryTimeoutMs] == f"{query_timeout_ms}"
    assert request.headers[Header.Traceparent] == traceparent
    assert request.headers[Header.Typecheck] == str(typecheck).lower()
    assert request.headers[Header.MaxContentionRetries] == f"{max_contention_retries}"  # yapf: disable
    assert request.headers[Header.Tags] == "project=teapot,hello=world,testing=foobar"  # yapf: disable
    assert request.headers["additional"] == "header"

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
            typecheck=typecheck,
            additional_headers=additional_headers,
        ),
    )


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

  httpx_mock.add_callback(validate_tags, is_reusable=True)

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

  httpx_mock.add_callback(validate_headers, is_reusable=True)

  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)

    with subtests.test("should allow for custom header on Client"):
      expected = {"happy": "fox"}
      c = Client(
          http_client=http_client,
          additional_headers=expected,
      )
      c.query(fql("just a mock"))

    with subtests.test("Linearized should be set on Client"):
      c = Client(
          http_client=http_client,
          linearized=True,
      )
      expected = {Header.Linearized: "true"}
      c.query(fql("just a mock"))

    with subtests.test("Max Contention Retries on Client"):
      count = 5

      c = Client(
          http_client=http_client,
          max_contention_retries=count,
      )

      expected = {Header.MaxContentionRetries: f"{count}"}
      c.query(fql("just a mock"))

    with subtests.test("Typecheck on Client"):
      c = Client(
          http_client=http_client,
          typecheck=True,
      )

      expected = {Header.Typecheck: "true"}
      c.query(fql("just a mock"))


def test_error_query_check_error(subtests, httpx_mock: HTTPXMock):

  def callback(_: httpx.Request):
    return httpx.Response(
        status_code=400,
        json={"error": {
            "code": "invalid_query",
            "message": "did not jump"
        }},
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
    err = "400: Response is in an unknown format: \n{'data': 'jumped'}"
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
    err = "400: Response is in an unknown format: \n{'error': {'message': 'boo'}}"
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
    err = "400: Response is in an unknown format: \n{'error': {'code': 'boo'}}"
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
    err = "200: Response is in an unknown format: \n{}"
    with pytest.raises(ProtocolError, match=err):
      c.query(fql("the quick brown fox"))


def test_call_query_with_string():
  c = Client()
  with pytest.raises(
      TypeError,
      match="'fql' must be a Query but was a <class 'str'>. You can build a Query by "
      "calling fauna.fql()"):
    c.query("fake")  # type: ignore


def test_client_stream(subtests, httpx_mock: HTTPXMock):
  response = [
      b'{"type": "status", "txn_ts": 1, "cursor": "a"}\n',
      b'{"type": "add", "txn_ts": 2, "cursor": "b"}\n',
      b'{"type": "remove", "txn_ts": 3, "cursor": "c"}\n'
  ]

  httpx_mock.add_response(stream=IteratorStream(response))

  ret = []
  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    c = Client(http_client=http_client)
    with c.stream(EventSource("token")) as stream:
      ret = [obj for obj in stream]

      assert stream.last_ts == 3

  assert ret == [{
      "type": "add",
      "txn_ts": 2,
      "cursor": "b"
  }, {
      "type": "remove",
      "txn_ts": 3,
      "cursor": "c"
  }]


def test_client_close_stream(subtests, httpx_mock: HTTPXMock):
  response = [
      b'{"type": "status", "txn_ts": 1, "cursor": "a"}\n',
      b'{"type": "add", "txn_ts": 2, "cursor": "b"}\n'
  ]

  httpx_mock.add_response(stream=IteratorStream(response))

  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    c = Client(http_client=http_client)
    with c.stream(EventSource("token")) as stream:
      assert next(stream) == {"type": "add", "txn_ts": 2, "cursor": "b"}
      stream.close()

      assert stream.last_ts == 2

      with pytest.raises(StopIteration):
        next(stream)


def test_client_retry_stream(subtests, httpx_mock: HTTPXMock):

  def stream_iter0():
    yield b'{"type": "status", "txn_ts": 1, "cursor": "a"}\n'
    yield b'{"type": "add", "txn_ts": 2, "cursor": "b"}\n'
    raise NetworkError("Some network error")
    yield b'{"type": "status", "txn_ts": 3, "cursor": "c"}\n'

  def stream_iter1():
    yield b'{"type": "status", "txn_ts": 4, "cursor": "d"}\n'

  httpx_mock.add_response(stream=IteratorStream(stream_iter0()))
  httpx_mock.add_response(stream=IteratorStream(stream_iter1()))

  ret = []
  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    c = Client(http_client=http_client)
    with c.stream(EventSource("token")) as stream:
      ret = [obj for obj in stream]

      assert stream.last_ts == 4

  assert ret == [{"type": "add", "txn_ts": 2, "cursor": "b"}]


def test_client_close_stream_on_error(subtests, httpx_mock: HTTPXMock):

  def stream_iter():
    yield b'{"type": "status", "txn_ts": 1, "cursor": "a"}\n'
    yield b'{"type": "add", "txn_ts": 2, "cursor": "b"}\n'
    yield b'{"type": "error", "txn_ts": 3, "error": {"message": "message", "code": "abort"}}\n'
    yield b'{"type": "status", "txn_ts": 4, "cursor": "c"}\n'

  httpx_mock.add_response(stream=IteratorStream(stream_iter()))

  ret = []

  with pytest.raises(AbortError):
    with httpx.Client() as mockClient:
      http_client = HTTPXClient(mockClient)
      c = Client(http_client=http_client)
      with c.stream(EventSource("token")) as stream:
        for obj in stream:
          ret.append(obj)

      assert stream.last_ts == 5

  assert ret == [{"type": "add", "txn_ts": 2, "cursor": "b"}]


def test_client_ignore_start_event(subtests, httpx_mock: HTTPXMock):

  def stream_iter():
    yield b'{"type": "start", "txn_ts": 1}\n'
    yield b'{"type": "status", "txn_ts": 2, "cursor": "a"}\n'
    yield b'{"type": "add", "txn_ts": 3, "cursor": "b"}\n'
    yield b'{"type": "remove", "txn_ts": 4, "cursor": "c"}\n'
    yield b'{"type": "status", "txn_ts": 5, "cursor": "d"}\n'

  httpx_mock.add_response(stream=IteratorStream(stream_iter()))

  ret = []

  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    c = Client(http_client=http_client)
    with c.stream(EventSource("token")) as stream:
      for obj in stream:
        ret.append(obj)

      assert stream.last_ts == 5

  assert ret == [{
      "type": "add",
      "txn_ts": 3,
      "cursor": "b"
  }, {
      "type": "remove",
      "txn_ts": 4,
      "cursor": "c"
  }]


def test_client_handle_status_events(subtests, httpx_mock: HTTPXMock):

  def stream_iter():
    yield b'{"type": "status", "txn_ts": 1}\n'
    yield b'{"type": "add", "txn_ts": 2}\n'
    yield b'{"type": "remove", "txn_ts": 3}\n'
    yield b'{"type": "status", "txn_ts": 4}\n'

  httpx_mock.add_response(stream=IteratorStream(stream_iter()))

  ret = []

  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    c = Client(http_client=http_client)
    with c.stream(EventSource("token"),
                  StreamOptions(status_events=True)) as stream:
      for obj in stream:
        ret.append(obj)

      assert stream.last_ts == 4

  assert ret == [{
      "type": "status",
      "txn_ts": 1
  }, {
      "type": "add",
      "txn_ts": 2
  }, {
      "type": "remove",
      "txn_ts": 3
  }, {
      "type": "status",
      "txn_ts": 4
  }]
