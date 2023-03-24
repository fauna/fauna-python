from dataclasses import dataclass
from enum import Enum
from typing import Optional, Mapping, Any, Union, List


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
        """The tags associated with the query."""
        return self._query_tags

    @property
    def summary(self) -> str:
        """A comprehensive, human readable summary of any errors, warnings and/or logs returned from the query."""
        return self._summary

    @property
    def stats(self) -> Mapping[Union[str, QueryStat], Any]:
        """Query stats associated with the query."""
        return self._stats

    @property
    def txn_ts(self) -> int:
        return self._txn_ts

    def __init__(
        self,
        query_tags: Optional[Mapping[str, str]] = None,
        stats: Optional[Mapping[Union[str, QueryStat], Any]] = None,
        summary: Optional[str] = None,
        txn_ts: Optional[int] = None,
    ):
        self._query_tags = query_tags or {}
        self._stats = stats or {}
        self._summary = summary or ""
        self._txn_ts = txn_ts or 0

    def __repr__(self):
        return f"{self.__class__.__name__}(" \
               f"query_tags={repr(self.query_tags)}," \
               f"stats={repr(self.stats)}," \
               f"summary={repr(self.summary)}," \
               f"txn_ts={repr(self.txn_ts)})"


class QuerySuccess(QueryInfo):
    """The result of the query."""

    @property
    def data(self) -> Any:
        """The data returned by the query. This is the result of the FQL query."""
        return self._data

    @property
    def static_type(self) -> Optional[str]:
        """If typechecked, the query's inferred static result type, if the query was typechecked."""
        return self._static_type

    @property
    def traceparent(self) -> Optional[str]:
        """The traceparent for the query."""
        return self._traceparent

    def __init__(
        self,
        data: Any,
        query_tags: Optional[Mapping[str, str]],
        static_type: Optional[str],
        stats: Optional[Mapping[str, Any]],
        summary: Optional[str],
        traceparent: Optional[str],
        txn_ts: Optional[int],
    ):

        super().__init__(query_tags=query_tags,
                         stats=stats,
                         summary=summary,
                         txn_ts=txn_ts)

        self._traceparent = traceparent
        self._static_type = static_type
        self._data = data

    def __repr__(self):
        return f"{self.__class__.__name__}(" \
               f"query_tags={repr(self.query_tags)}," \
               f"static_type={repr(self.static_type)}," \
               f"stats={repr(self.stats)}," \
               f"summary={repr(self.summary)}," \
               f"traceparent={repr(self.traceparent)}," \
               f"txn_ts={repr(self.txn_ts)}," \
               f"data={repr(self.data)})"


@dataclass
class ConstraintFailure:
    message: str
    name: Optional[str] = None
    paths: Optional[List[Any]] = None


class QueryTags:

    @staticmethod
    def encode(tags: Mapping[str, str]) -> str:
        return ",".join([f"{k}={v}" for k, v in tags.items()])

    @staticmethod
    def decode(tag_str: str) -> Mapping[str, str]:
        res: dict[str, str] = {}
        for pair in tag_str.split(","):
            kv = pair.split("=")
            res[kv[0]] = kv[1]
        return res
