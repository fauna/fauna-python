from __future__ import annotations

from typing import Any, Mapping

from .http_client import HTTPResponse


class Response:

    @property
    def data(self) -> Any:
        return self._data

    @property
    def headers(self) -> Mapping[str, str]:
        return self._headers

    @property
    def stats(self) -> Mapping[str, int]:
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
        self._stats = {}

        response_json = http_response.json()

        self._headers = http_response.headers()

        self._status_code = http_response.status_code()
        self._traceparent = http_response.headers().get("traceparent", "")

        http_response.close()

        if "stats" in response_json:
            self._stats = response_json["stats"]

        if "summary" in response_json:
            self._summary = response_json["summary"]

        if "data" in response_json:
            self._data = response_json["data"]
        else:
            raise Exception("Unexpected response")
