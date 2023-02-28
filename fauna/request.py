import urllib.parse
from typing import Dict, Optional, Mapping
from .headers import Header


class QueryOptions:
    """
    Set options on a query

    :param linearized: If true, unconditionally run the query as strictly serialized.
    This affects read-only transactions. Transactions which write will always be strictly serialized.
    :param max_contention_retries: The max number of times to retry the query if contention is encountered.
    :param query_timeout_ms: Controls the maximum amount of time (in milliseconds) Fauna will execute your query before marking it failed.
    :param tags: Tags provided back via logging and telemetry.
    :param traceparent:  A traceparent provided back via logging and telemetry.
    Must match format: https://www.w3.org/TR/trace-context/#traceparent-header
    """

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
            self._headers[Header.Tags] = urllib.parse.urlencode(tags)

        if traceparent is not None:
            self._headers[Header.Traceparent] = traceparent

    def headers(self) -> Dict[str, str]:
        return self._headers
