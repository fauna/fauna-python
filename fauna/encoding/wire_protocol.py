from dataclasses import dataclass
from typing import Optional, Mapping, Any, List


class QueryStats:
  """Query stats"""

  @property
  def compute_ops(self) -> int:
    """The amount of Transactional Compute Ops consumed by the query."""
    return self._compute_ops

  @property
  def read_ops(self) -> int:
    """The amount of Transactional Read Ops consumed by the query."""
    return self._read_ops

  @property
  def write_ops(self) -> int:
    """The amount of Transactional Write Ops consumed by the query."""
    return self._write_ops

  @property
  def query_time_ms(self) -> int:
    """The query run time in milliseconds."""
    return self._query_time_ms

  @property
  def storage_bytes_read(self) -> int:
    """The amount of data read from storage, in bytes."""
    return self._storage_bytes_read

  @property
  def storage_bytes_write(self) -> int:
    """The amount of data written to storage, in bytes."""
    return self._storage_bytes_write

  @property
  def contention_retries(self) -> int:
    """The number of times the transaction was retried due to write contention."""
    return self._contention_retries

  def __init__(self, stats: Mapping[str, Any]):
    self._compute_ops = stats.get("compute_ops", 0)
    self._read_ops = stats.get("read_ops", 0)
    self._write_ops = stats.get("write_ops", 0)
    self._query_time_ms = stats.get("query_time_ms", 0)
    self._storage_bytes_read = stats.get("storage_bytes_read", 0)
    self._storage_bytes_write = stats.get("storage_bytes_write", 0)
    self._contention_retries = stats.get("contention_retries", 0)

  def __repr__(self):
    stats = {
        "compute_ops": self._compute_ops,
        "read_ops": self._read_ops,
        "write_ops": self._write_ops,
        "query_time_ms": self._query_time_ms,
        "storage_bytes_read": self._storage_bytes_read,
        "storage_bytes_write": self._storage_bytes_write,
        "contention_retries": self._contention_retries,
    }

    return f"{self.__class__.__name__}(stats={repr(stats)})"

  def __eq__(self, other):
    return type(self) == type(other) \
        and self.compute_ops == other.compute_ops \
        and self.read_ops == other.read_ops \
        and self.write_ops == other.write_ops \
        and self.query_time_ms == other.query_time_ms \
        and self.storage_bytes_read == other.storage_bytes_read \
        and self.storage_bytes_write == other.storage_bytes_write \
        and self.contention_retries == other.contention_retries

  def __ne__(self, other):
    return not self.__eq__(other)


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
  def stats(self) -> QueryStats:
    """Query stats associated with the query."""
    return self._stats

  @property
  def txn_ts(self) -> int:
    """The last transaction timestamp of the query. A Unix epoch in microseconds."""
    return self._txn_ts

  @property
  def schema_version(self) -> int:
    """The schema version that was used for the query execution."""
    return self._schema_version

  def __init__(
      self,
      query_tags: Optional[Mapping[str, str]] = None,
      stats: Optional[QueryStats] = None,
      summary: Optional[str] = None,
      txn_ts: Optional[int] = None,
      schema_version: Optional[int] = None,
  ):
    self._query_tags = query_tags or {}
    self._stats = stats or QueryStats({})
    self._summary = summary or ""
    self._txn_ts = txn_ts or 0
    self._schema_version = schema_version or 0

  def __repr__(self):
    return f"{self.__class__.__name__}(" \
           f"query_tags={repr(self.query_tags)}," \
           f"stats={repr(self.stats)}," \
           f"summary={repr(self.summary)}," \
           f"txn_ts={repr(self.txn_ts)}," \
           f"schema_version={repr(self.schema_version)})"


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
      stats: Optional[QueryStats],
      summary: Optional[str],
      traceparent: Optional[str],
      txn_ts: Optional[int],
      schema_version: Optional[int],
  ):

    super().__init__(
        query_tags=query_tags,
        stats=stats,
        summary=summary,
        txn_ts=txn_ts,
        schema_version=schema_version,
    )

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
           f"schema_version={repr(self.schema_version)}," \
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
