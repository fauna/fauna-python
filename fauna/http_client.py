import abc
from typing import Optional, Iterator, Mapping, Any
import httpx

DefaultHttpConnectTimeout = 1 * 60
DefaultHttpReadTimeout = 1 * 60
DefaultHttpWriteTimeout = 1 * 60
DefaultHttpPoolTimeout = DefaultHttpReadTimeout
DefaultIdleConnectionTimeout = 4
DefaultMaxConnections = 20
DefaultMaxIdleConnections = 20


class HTTPResponse(abc.ABC):

    @abc.abstractmethod
    def headers(self) -> Mapping[str, str]:
        pass

    @abc.abstractmethod
    def status_code(self) -> int:
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

    def status_code(self) -> int:
        return self._r.status_code

    def read(self) -> bytes:
        return self._r.read()

    def iter_bytes(self, size: Optional[int] = None) -> Iterator[bytes]:
        return self._r.iter_bytes(size)

    def close(self) -> None:
        self._r.close()


class HTTPXClient(HTTPClient):

    def __init__(self, client: Optional[httpx.Client] = None):
        super(HTTPXClient, self).__init__()

        if client is not None:
            self._c = client
        else:
            self._c = httpx.Client(
                http1=False,
                http2=True,
                timeout=httpx.Timeout(
                    connect=DefaultHttpConnectTimeout,
                    read=DefaultHttpReadTimeout,
                    write=DefaultHttpWriteTimeout,
                    pool=DefaultHttpPoolTimeout,
                ),
                limits=httpx.Limits(
                    max_connections=DefaultMaxConnections,
                    max_keepalive_connections=DefaultMaxIdleConnections,
                    keepalive_expiry=DefaultIdleConnectionTimeout,
                ),
            )

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
            data=data,
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
        response = self._c.stream("POST", url, data=data, headers=headers)
        for r in response:
            yield HTTPXResponse(r)
