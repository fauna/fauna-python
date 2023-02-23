from __future__ import annotations

from typing import Any, Mapping
from enum import Enum

from .http_client import HTTPResponse


class Stat(str, Enum):
    ComputeOps = "x-compute-ops"


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

    def stat(self, key: Stat) -> int:
        if key in self._headers:
            return int(self._headers[key])

        return 0