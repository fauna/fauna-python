import json

import httpx
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
    ret = [obj for obj in http_client.stream("http://localhost:8443", {}, {})]

    assert ret == expected
