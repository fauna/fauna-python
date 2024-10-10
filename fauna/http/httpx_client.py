import json
import logging
from contextlib import contextmanager
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

  def text(self) -> str:
    return str(self.read(), encoding='utf-8')

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

  def __init__(self,
               client: httpx.Client,
               logger: logging.Logger = logging.getLogger("fauna")):
    super(HTTPXClient, self).__init__()
    self._c = client
    self._logger = logger

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

      if self._logger.isEnabledFor(logging.DEBUG):
        headers_to_log = request.headers.copy()
        headers_to_log.pop("Authorization")
        self._logger.debug(
            f"query.request method={request.method} url={request.url} headers={headers_to_log} data={data}"
        )

    except httpx.InvalidURL as e:
      raise ClientError("Invalid URL Format") from e

    try:
      response = self._c.send(
          request,
          stream=False,
      )

      if self._logger.isEnabledFor(logging.DEBUG):
        self._logger.debug(
            f"query.response status_code={response.status_code} headers={response.headers} data={response.text}"
        )

      return HTTPXResponse(response)
    except (httpx.HTTPError, httpx.InvalidURL) as e:
      raise NetworkError("Exception re-raised from HTTP request") from e

  @contextmanager
  def stream(
      self,
      url: str,
      headers: Mapping[str, str],
      data: Mapping[str, Any],
  ) -> Iterator[Any]:
    request = self._c.build_request(
        method="POST",
        url=url,
        headers=headers,
        json=data,
    )

    if self._logger.isEnabledFor(logging.DEBUG):
      headers_to_log = request.headers.copy()
      headers_to_log.pop("Authorization")
      self._logger.debug(
          f"stream.request method={request.method} url={request.url} headers={headers_to_log} data={data}"
      )

    response = self._c.send(
        request=request,
        stream=True,
    )

    try:
      yield self._transform(response)
    finally:
      response.close()

  def _transform(self, response):
    try:
      for line in response.iter_lines():
        loaded = json.loads(line)
        if self._logger.isEnabledFor(logging.DEBUG):
          self._logger.debug(f"stream.data data={loaded}")
        yield loaded
    except httpx.ReadTimeout as e:
      raise NetworkError("Stream timeout") from e
    except (httpx.HTTPError, httpx.InvalidURL) as e:
      raise NetworkError("Exception re-raised from HTTP request") from e

  def close(self):
    self._c.close()
