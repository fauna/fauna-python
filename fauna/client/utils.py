import os
import threading
from typing import Generic, Callable, TypeVar, Optional

from fauna.client.endpoints import Endpoints
from fauna.client.headers import Header


def _fancy_bool_from_str(val: str) -> bool:
  return val.lower() in ["1", "true", "yes", "y"]


class LastTxnTs(object):
  """Wraps tracking the last transaction time supplied from the database."""

  def __init__(
      self,
      time: Optional[int] = None,
  ):
    self._lock: threading.Lock = threading.Lock()
    self._time: Optional[int] = time

  @property
  def time(self):
    """Produces the last transaction time, or, None if not yet updated."""
    with self._lock:
      return self._time

  @property
  def request_header(self):
    """Produces a dictionary with a non-zero `X-Last-Seen-Txn` header; or,
        if one has not yet been set, the empty header dictionary."""
    t = self._time
    if t is None:
      return {}
    return {Header.LastTxnTs: str(t)}

  def update_txn_time(self, new_txn_time: int):
    """Updates the internal transaction time.
        In order to maintain a monotonically-increasing value, `newTxnTime`
        is discarded if it is behind the current timestamp."""
    with self._lock:
      self._time = max(self._time or 0, new_txn_time)


T = TypeVar('T')


class _SettingFromEnviron(Generic[T]):

  def __init__(
      self,
      var_name: str,
      default_value: str,
      adapt_from_str: Callable[[str], T],
  ):
    self.__var_name = var_name
    self.__default_value = default_value
    self.__adapt_from_str = adapt_from_str

  def __call__(self) -> T:
    return self.__adapt_from_str(
        os.environ.get(
            self.__var_name,
            default=self.__default_value,
        ))


class _Environment:
  EnvFaunaEndpoint = _SettingFromEnviron(
      "FAUNA_ENDPOINT",
      Endpoints.Default,
      str,
  )
  """environment variable for Fauna Client HTTP endpoint"""

  EnvFaunaSecret = _SettingFromEnviron(
      "FAUNA_SECRET",
      "",
      str,
  )
  """environment variable for Fauna Client authentication"""
