from __future__ import annotations

from typing import Any, Mapping
from dataclasses import dataclass

from .http_client import HTTPResponse


@dataclass
class Stats:
    byte_read_ops: int = 0
    byte_write_ops: int = 0
    contention_retries: int = 0
    compute_ops: int = 0
    query_bytes_in: int = 0
    query_bytes_out: int = 0
    query_time_ms: int = 0
    read_ops: int = 0
    storage_bytes_read: int = 0
    storage_bytes_write: int = 0
    txn_retries: int = 0
    write_ops: int = 0


class Response:

    @property
    def data(self) -> Any:
        return self._data

    @property
    def headers(self) -> Mapping[str, str]:
        return self._headers

    @property
    def stats(self) -> Stats:
        return self._stats

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
        # initialize an empty mapping
        self._stats = Stats()

        response_json = http_response.json()

        self._headers = http_response.headers()

        self._status_code = http_response.status_code()
        self._traceparent = http_response.headers().get("traceparent", "")

        http_response.close()

        for k, v in self._headers.items():
            key = k.lower().removeprefix("x-").replace("-", "_")
            if hasattr(self._stats, key):
                setattr(self._stats, key, int(v))

        if "summary" in response_json:
            self._summary = response_json["summary"]

        if "data" in response_json:
            self._data = response_json["data"]
        else:
            raise Exception("Unexpected response")
