from typing import Optional, List, Any, Mapping

from fauna.encoding import ConstraintFailure, QueryStats, QueryInfo


class FaunaException(Exception):
  """Base class Fauna Exceptions"""
  pass


class ClientError(FaunaException):
  """An error representing a failure internal to the client, itself.
    This indicates Fauna was never called - the client failed internally
    prior to sending the request."""
  pass


class NetworkError(FaunaException):
  """An error representing a failure due to the network.
    This indicates Fauna was never reached."""
  pass


class ProtocolError(FaunaException):
  """An error representing a HTTP failure - but one not directly emitted by Fauna."""

  @property
  def status_code(self) -> int:
    return self._status_code

  @property
  def message(self) -> str:
    return self._message

  def __init__(self, status_code: int, message: str):
    self._status_code = status_code
    self._message = message

  def __str__(self):
    return f"{self.status_code}: {self.message}"


class FaunaError(FaunaException):
  """Base class Fauna Errors"""

  @property
  def status_code(self) -> int:
    return self._status_code

  @property
  def code(self) -> str:
    return self._code

  @property
  def message(self) -> str:
    return self._message

  @property
  def abort(self) -> Optional[Any]:
    return self._abort

  @property
  def constraint_failures(self) -> Optional[List['ConstraintFailure']]:
    return self._constraint_failures

  def __init__(
      self,
      status_code: int,
      code: str,
      message: str,
      abort: Optional[Any] = None,
      constraint_failures: Optional[List['ConstraintFailure']] = None,
  ):
    self._status_code = status_code
    self._code = code
    self._message = message
    self._abort = abort
    self._constraint_failures = constraint_failures

  def __str__(self):
    return f"{self.status_code}: {self.code}\n{self.message}"


class ServiceError(FaunaError, QueryInfo):
  """An error representing a query failure returned by Fauna."""

  def __init__(
      self,
      status_code: int,
      code: str,
      message: str,
      summary: Optional[str] = None,
      abort: Optional[Any] = None,
      constraint_failures: Optional[List['ConstraintFailure']] = None,
      query_tags: Optional[Mapping[str, str]] = None,
      stats: Optional[QueryStats] = None,
      txn_ts: Optional[int] = None,
      schema_version: Optional[int] = None,
  ):
    QueryInfo.__init__(
        self,
        query_tags=query_tags,
        stats=stats,
        summary=summary,
        txn_ts=txn_ts,
        schema_version=schema_version,
    )

    FaunaError.__init__(
        self,
        status_code=status_code,
        code=code,
        message=message,
        abort=abort,
        constraint_failures=constraint_failures,
    )

  def __str__(self):
    constraint_str = "---"
    if self._constraint_failures:
      constraint_str = f"---\nconstraint failures: {self._constraint_failures}\n---"

    return f"{self._status_code}: {self.code}\n{self.message}\n{constraint_str}\n{self.summary or ''}"


class AbortError(ServiceError):
  pass


class InvalidRequestError(ServiceError):
  pass


class QueryCheckError(ServiceError):
  """An error due to a "compile-time" check of the query failing."""
  pass


class QueryRuntimeError(ServiceError):
  """An error response that is the result of the query failing during execution.
    QueryRuntimeError's occur when a bug in your query causes an invalid execution
    to be requested.
    The 'code' field will vary based on the specific error cause."""
  pass


class AuthenticationError(ServiceError):
  """AuthenticationError indicates invalid credentials were used."""
  pass


class AuthorizationError(ServiceError):
  """AuthorizationError indicates the credentials used do not have
    permission to perform the requested action."""
  pass


class ThrottlingError(ServiceError):
  """ThrottlingError indicates some capacity limit was exceeded
    and thus the request could not be served."""
  pass


class QueryTimeoutError(ServiceError):
  """A failure due to the timeout being exceeded, but the timeout
    was set lower than the query's expected processing time.
    This response is distinguished from a ServiceTimeoutException
    in that a QueryTimeoutError shows Fauna behaving in an expected manner."""
  pass


class ServiceInternalError(ServiceError):
  """ServiceInternalError indicates Fauna failed unexpectedly."""
  pass


class ServiceTimeoutError(ServiceError):
  """ServiceTimeoutError indicates Fauna was not available to service
    the request before the timeout was reached."""
  pass
