import urllib.parse
from typing import Dict, Optional, Mapping
from .headers import Header


class QueryOptions:

    @property
    def options(self) -> Dict[str, str]:
        return self._opts

    def __init__(
        self,
        linearized: Optional[bool] = None,
        max_contention_retries: Optional[int] = None,
        query_timeout_ms: Optional[int] = None,
        query_tags: Optional[Mapping[str, str]] = None,
        traceparent: Optional[str] = None,
    ):
        """
        A class representing options available for a query.

        :param linearized: If true, unconditionally run the query as strictly serialized.
            This affects read-only transactions. Transactions which write will always be strictly serialized.
        :param max_contention_retries: The max number of times to retry the query if contention is encountered.
        :param query_timeout_ms: Controls the maximum amount of time (in milliseconds) Fauna will execute your query before marking it failed.
        :param query_tags: Tags to associate with the query. See `logging <https://docs.fauna.com/fauna/current/build/logs/query_log/>`_
        :param traceparent:  A traceparent to associate with the query. See `logging <https://docs.fauna.com/fauna/current/build/logs/query_log/>`_
            Must match format: https://www.w3.org/TR/trace-context/#traceparent-header
        """

        self._opts: dict[str, str] = {}

        if linearized is not None:
            self._opts[Header.Linearized] = str(linearized).lower()

        if max_contention_retries is not None and max_contention_retries > 0:
            self._opts[
                Header.MaxContentionRetries] = f"{max_contention_retries}"

        if query_timeout_ms is not None and query_timeout_ms > 0:
            self._opts[Header.TimeoutMs] = f"{query_timeout_ms}"

        if query_tags is not None:
            self._opts[Header.Tags] = urllib.parse.urlencode(query_tags)

        if traceparent is not None:
            self._opts[Header.Traceparent] = traceparent
