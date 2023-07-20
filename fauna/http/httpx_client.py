import json
from json import JSONDecodeError
from typing import Mapping, Any, Optional, Iterator

import httpx

from fauna.errors import ClientError, NetworkError
from fauna.http.http_client import HTTPResponse, HTTPClient


class HTTPXResponse(HTTPResponse):

  def __init__(self, response: httpx.Response):
    self._r = response

  def headers(self) -> Mapping[str, str]:
    h = {}
    for (k, v) in self._r.headers.items():
      h[k] = v
    return h

  def json(self) -> Any:
    try:
      decoded = self._r.read().decode("utf-8")
      return json.loads(decoded)
    except (JSONDecodeError, UnicodeDecodeError) as e:
      raise ClientError(
          f"Unable to decode response from endpoint {self._r.request.url}. Check that your endpoint is valid."
      ) from e

  def status_code(self) -> int:
    return self._r.status_code

  def read(self) -> bytes:
    return self._r.read()

  def iter_bytes(self, size: Optional[int] = None) -> Iterator[bytes]:
    return self._r.iter_bytes(size)

  def close(self) -> None:
    try:
      self._r.close()
    except Exception as e:
      raise ClientError("Error closing response") from e


class HTTPXClient(HTTPClient):

  def __init__(self, client: httpx.Client):
    super(HTTPXClient, self).__init__()
    self._c = client

  def request(
      self,
      method: str,
      url: str,
      headers: Mapping[str, str],
      data: Mapping[str, Any],
  ) -> HTTPResponse:

    try:
      request = self._c.build_request(
          method,
          url,
          json=data,
          headers=headers,
      )
    except httpx.InvalidURL as e:
      raise ClientError("Invalid URL Format") from e

    try:
      response = self._c.send(
          request,
          stream=False,
      )
    except (httpx.HTTPError, httpx.InvalidURL) as e:
      raise NetworkError("Exception re-raised from HTTP request") from e

    return HTTPXResponse(response)

  def stream(
      self,
      url: str,
      headers: Mapping[str, str],
      data: Mapping[str, Any],
  ) -> Iterator[HTTPResponse]:
    raise NotImplementedError()
