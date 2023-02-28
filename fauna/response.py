from enum import Enum
from typing import Any, Mapping

from .http_client import HTTPResponse


class Stat(str, Enum):
    ByteReadOps = "x-byte-read-ops"
    ByteWRiteOps = "x-byte-write-ops"
    ComputeOps = "x-compute-ops"
    QueryBytesIn = "x-query-bytes-in"
    QueryBytesOut = "x-query-bytes-out"
    ReadOps = "x-read-ops"
    StorageBytesRead = "x-storage-bytes-read"
    StorageBytesWrite = "x-storage-bytes-write"
    TxnRetries = "x-txn-retries"
    WriteOps = "x-write-ops"


class Response:

    @property
    def data(self) -> Any:
        return self._data

    @property
    def headers(self) -> Mapping[str, str]:
        return self._headers

    @property
    def summary(self) -> str:
        return self._summary

    @property
    def traceparent(self) -> str:
        return self._traceparent

    @property
    def status_code(self) -> int:
        return self._status_code

    def __init__(self, http_response: HTTPResponse):
        response_json = http_response.json()

        self._headers = http_response.headers()

        self._status_code = http_response.status_code()
        self._traceparent = http_response.headers().get("traceparent", "")

        http_response.close()

        if "summary" in response_json:
            self._summary = response_json["summary"]

        if "data" in response_json:
            self._data = response_json["data"]
        else:
            raise Exception("Unexpected response")

    def stat(self, key: str) -> int:
        """
        Return the value of the Stat by key. You can use the :type:`Stat` :type:`Enum`
        or pass a known string for any stat that have not been added to the Enum.

        :param key: key for the stat Header
        :raises KeyError: Unknown stat key
        """
        return int(self._headers[key])
