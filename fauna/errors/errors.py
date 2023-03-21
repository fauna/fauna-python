from typing import Optional, List

from fauna.client.wire_protocol import ConstraintFailure, QueryInfo


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

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ):
        self._status_code = status_code
        self._code = code
        self._message = message

    def __str__(self):
        return f"{self.status_code}: {self.code}\n{self.message}"


class ProtocolError(FaunaError):
    """An error representing a HTTP failure - but one not directly emitted by Fauna."""
    pass


class ServiceError(FaunaError):
    """An error representing a query failure returned by Fauna."""

    @property
    def constraint_failures(self) -> Optional[List[ConstraintFailure]]:
        return self._constraint_failures

    @property
    def query_info(self) -> Optional[QueryInfo]:
        return self._query_info

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        query_info: Optional[QueryInfo] = None,
        constraint_failures: Optional[List[ConstraintFailure]] = None,
    ):
        """
        :param status_code: The HTTP status code of the error.
        :param code: A code for the error. Codes indicate the cause of the error. It is safe to write programmatic logic against the code. They are part of the API contract.
        :param message: A short, human readable description of the error.
        :param query_info: A :class:`QueryInfo` instance
        :param constraint_failures: When the code is 'constraint_failure', an array of write constraint failures associated with the error.
        """
        super().__init__(status_code, code, message)

        self._query_info = query_info
        self._constraint_failures = constraint_failures

    def __str__(self):
        constraint_str = "---"
        if self._constraint_failures:
            constraint_str = f"---\nconstraint failures: {self._constraint_failures}\n---"

        summary = ""
        if self._query_info is not None:
            summary = self._query_info.summary

        return f"{self._status_code}: {self._code}\n{self._message}\n{constraint_str}\n{summary}"


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
