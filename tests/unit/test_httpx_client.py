import json

import httpx
import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from fauna.client import Client
from fauna.http import HTTPXClient


def test_httx_client_stream(subtests, httpx_mock: HTTPXMock):
  expected = [{"@int": "10"}, {"@long": "20"}]

  def to_json_bytes(obj):
    return bytes(json.dumps(obj) + "\n", "utf-8")

  httpx_mock.add_response(
      stream=IteratorStream([to_json_bytes(obj) for obj in expected]))

  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    with http_client.stream("http://localhost:8443", {}, {}) as stream:
      ret = [obj for obj in stream]

      assert ret == expected


def test_httx_client_close_stream(subtests, httpx_mock: HTTPXMock):
  expected = [{"@int": "10"}, {"@long": "20"}]

  def to_json_bytes(obj):
    return bytes(json.dumps(obj) + "\n", "utf-8")

  httpx_mock.add_response(
      stream=IteratorStream([to_json_bytes(obj) for obj in expected]))

  with httpx.Client() as mockClient:
    http_client = HTTPXClient(mockClient)
    with http_client.stream("http://localhost:8443", {}, {}) as stream:
      next(stream) == expected[0]
      stream.close()

      with pytest.raises(StopIteration):
        next(stream)
