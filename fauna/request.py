from typing import Any, Dict, Optional, Mapping
from .headers import Header


class QueryOptions:

    def __init__(
        self,
        linearized: Optional[bool] = None,
        max_contention_retries: Optional[int] = None,
        query_timeout_ms: Optional[int] = None,
        tags: Optional[Mapping[str, str]] = None,
        traceparent: Optional[str] = None,
    ):
        self._headers: dict[str, str] = {}

        if linearized is not None:
            self._headers[Header.Linearized] = str(linearized).lower()

        if max_contention_retries is not None and max_contention_retries > 0:
            self._headers[
                Header.MaxContentionRetries] = f"{max_contention_retries}"

        if query_timeout_ms is not None and query_timeout_ms > 0:
            self._headers[Header.TimeoutMs] = f"{query_timeout_ms}"

        if tags is not None:
            self._headers[Header.Tags] = '&'.join(
                [f"{k}={tags[k]}" for k in tags])

        if traceparent is not None:
            self._headers[Header.Traceparent] = traceparent

    def headers(self) -> Dict[str, str]:
        return self._headers
