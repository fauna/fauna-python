from dataclasses import dataclass
from enum import Enum
from typing import Optional, Mapping, Any, Union, List

from fauna.encoding import FaunaDecoder


class QueryStat(str, Enum):
    """Query stat names."""

    ComputeOps = "compute_ops"
    """The amount of Transactional Compute Ops consumed by the query."""

    ReadOps = "read_ops"
    """The amount of Transactional Read Ops consumed by the query."""

    WriteOps = "write_ops"
    """The amount of Transactional Write Ops consumed by the query."""

    QueryTimeMS = "query_time_ms"
    """The query run time in milliseconds."""

    StorageBytesRead = "storage_bytes_read"
    """The amount of data read from storage, in bytes."""

    StorageBytesWrite = "storage_bytes_write"
    """The amount of data written to storage, in bytes."""

    ContentionRetries = "contention_retries"
    """The number of times the transaction was retried due to write contention."""


class QueryInfo:

    @property
    def query_tags(self) -> Mapping[str, Any]:
        return self._query_tags

    @property
    def summary(self) -> str:
        return self._summary

    @property
    def stats(self) -> Mapping[Union[str, QueryStat], Any]:
        return self._stats

    @property
    def txn_ts(self) -> int:
        return self._txn_ts

    def __init__(
        self,
        query_tags: Optional[Mapping[str, Any]] = None,
        stats: Optional[Mapping[Union[str, QueryStat], Any]] = None,
        txn_ts: Optional[int] = None,
        summary: Optional[str] = None,
    ):
        self._txn_ts = txn_ts or 0
        self._query_tags = query_tags or {}
        self._stats = stats or {}
        self._summary = summary or ""


class QuerySuccess(QueryInfo):
    """The result of the query."""

    @property
    def data(self) -> Any:
        return self._data

    @property
    def static_type(self) -> Optional[str]:
        return self._static_type

    @property
    def traceparent(self) -> Optional[str]:
        return self._traceparent

    def __init__(
        self,
        body: Any,
        headers: Mapping[str, str],
    ):

        stats = body["stats"] if "stats" in body else None
        summary = body["summary"] if "summary" in body else None
        query_tags = body["query_tags"] if "query_tags" in body else None
        txn_ts = body["txn_ts"] if "txn_ts" in body else None
        super().__init__(query_tags=query_tags,
                         stats=stats,
                         summary=summary,
                         txn_ts=txn_ts)

        self._traceparent = headers.get("traceparent", None)
        self._static_type = body[
            "static_type"] if "static_type" in body else None
        self._data = FaunaDecoder.decode(body["data"])


@dataclass
class ConstraintFailure:
    message: str
    name: Optional[str] = None
    paths: Optional[List[Any]] = None
