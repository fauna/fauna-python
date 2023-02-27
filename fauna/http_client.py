import abc
import json
from typing import Optional, Iterator, Mapping, Any
from dataclasses import dataclass

import httpx


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
        self._r.close()


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

        request = self._c.build_request(
            method,
            url,
            json=data,
            headers=headers,
        )

        response = self._c.send(
            request,
            stream=False,
        )

        return HTTPXResponse(response)

    def stream(
        self,
        url: str,
        headers: Mapping[str, str],
        data: Mapping[str, Any],
    ) -> Iterator[HTTPResponse]:
        raise NotImplementedError()


class FaunaError(Exception):

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def code(self) -> str:
        return self._code

    @property
    def message(self) -> str:
        return self._message

    def __init__(self, status_code: int, code: str, message: str):
        self._status_code = status_code
        self._code = code
        self._message = message

    def __str__(self):
        return f"{self.status_code}: {self.code}\n{self.message}"


class ProtocolError(FaunaError):
    pass


class ServiceError(FaunaError):

    @property
    def summary(self) -> str:
        return self._summary

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        summary: str,
    ):
        super().__init__(status_code, code, message)

        self._summary = summary

    def __str__(self):
        return f"{self._status_code}: {self._code}\n{self._message}\n---\n{self._summary}"
