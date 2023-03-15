from enum import Enum
from typing import Any, Mapping, Union

from .wire_protocol import FaunaDecoder


class Stat(str, Enum):
    ByteReadOps = "byte_read_ops"
    ByteWRiteOps = "byte_write_ops"
    ComputeOps = "compute_ops"
    QueryBytesIn = "query_bytes_in"
    QueryBytesOut = "query_bytes_out"
    ReadOps = "read_ops"
    StorageBytesRead = "storage_bytes_read"
    StorageBytesWrite = "storage_bytes_write"
    TxnRetries = "txn_retries"
    WriteOps = "write_ops"


class QueryResponse:

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

    @property
    def stats(self) -> Mapping[Union[str, Stat], Any]:
        return self._stats

    def __init__(
        self,
        response_json: Any,
        headers: Mapping[str, str],
        status_code: int,
    ):

        self._status_code = status_code
        self._traceparent = headers.get("traceparent", "")
        self._headers = headers
        self._stats: Mapping[Union[str, Stat], Any] = {}

        if "summary" in response_json:
            self._summary = response_json["summary"]

        if "stats" in response_json:
            self._stats = response_json["stats"]

        self._data = FaunaDecoder.decode(response_json["data"])
