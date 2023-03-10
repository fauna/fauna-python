import abc
import json
from typing import Optional, Iterator, Mapping, Any
from dataclasses import dataclass

import httpx

from .errors import ClientError, NetworkError


@dataclass(frozen=True)
class ErrorResponse:
    status_code: int
    error_code: str
    error_message: str
    summary: str


class HTTPResponse(abc.ABC):

    @abc.abstractmethod
    def headers(self) -> Mapping[str, str]:
        pass

    @abc.abstractmethod
    def status_code(self) -> int:
        pass

    @abc.abstractmethod
    def json(self) -> Any:
        pass

    @abc.abstractmethod
    def read(self) -> bytes:
        pass

    @abc.abstractmethod
    def iter_bytes(self) -> Iterator[bytes]:
        pass

    @abc.abstractmethod
    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class HTTPClient(abc.ABC):

    # TODO(lucas): initialize base class with default retry strategy

    @abc.abstractmethod
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        data: Mapping[str, Any],
    ) -> HTTPResponse:
        pass

    @abc.abstractmethod
    def stream(
        self,
        url: str,
        headers: Mapping[str, str],
        data: Mapping[str, Any],
    ) -> HTTPResponse:
        pass


class HTTPXResponse(HTTPResponse):

    def __init__(self, response: httpx.Response):
        self._r = response

    def headers(self) -> Mapping[str, str]:
        h = {}
        for (k, v) in self._r.headers.items():
            h[k] = v
        return h

    def json(self) -> Any:
        return json.loads(self._r.read().decode("utf-8"))

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
