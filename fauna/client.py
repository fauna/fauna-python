import urllib.parse
from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import fauna
from fauna.response import QueryResponse
from fauna.errors import AuthenticationError, ClientError, ProtocolError, ServiceError, AuthorizationError, \
    ServiceInternalError, ServiceTimeoutError, ThrottlingException, QueryTimeoutException, QueryRuntimeError, \
    QueryCheckError
from fauna.headers import _DriverEnvironment, _Header, _Auth, Header
from fauna.http_client import HTTPClient, HTTPXClient
from fauna.query_builder import QueryBuilder
from fauna.utils import _Environment, LastTxnTs

DefaultHttpConnectTimeout = timedelta(seconds=5)
DefaultHttpReadTimeout: Optional[timedelta] = None
DefaultHttpWriteTimeout = timedelta(seconds=5)
DefaultHttpPoolTimeout = timedelta(seconds=5)
DefaultIdleConnectionTimeout = timedelta(seconds=5)
DefaultMaxConnections = 20
DefaultMaxIdleConnections = 20


@dataclass
class QueryOptions:
    """
    A dataclass representing options available for a query.

    * linearized - If true, unconditionally run the query as strictly serialized. This affects read-only transactions. Transactions which write will always be strictly serialized.
    * max_contention_retries - The max number of times to retry the query if contention is encountered.
    * query_timeout - Controls the maximum amount of time Fauna will execute your query before marking it failed.
    * query_tags - Tags to associate with the query. See `logging <https://docs.fauna.com/fauna/current/build/logs/query_log/>`_
    * traceparent - A traceparent to associate with the query. See `logging <https://docs.fauna.com/fauna/current/build/logs/query_log/>`_ Must match format: https://www.w3.org/TR/trace-context/#traceparent-header
    * additional_headers - Add/update HTTP request headers for the query. In general, this should not be necessary.
    """

    linearized: Optional[bool] = None
    max_contention_retries: Optional[int] = None
    query_timeout: Optional[timedelta] = None
    query_tags: Optional[Mapping[str, str]] = None
    traceparent: Optional[str] = None
    additional_headers: Optional[Dict[str, str]] = None


class Client:

    def __init__(
        self,
        endpoint: Optional[str] = None,
        secret: Optional[str] = None,
        http_client: Optional[HTTPClient] = None,
        query_tags: Optional[Mapping[str, str]] = None,
        linearized: Optional[bool] = None,
        max_contention_retries: Optional[int] = None,
        query_timeout: Optional[timedelta] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ):
        """Initializes a Client.

        :param endpoint: The Fauna Endpoint to use. Defaults to https://db.fauna.com, or the FAUNA_ENDPOINT env variable.
        :param secret: The Fauna Secret to use. Defaults to empty, or the FAUNA_SECRET env variable.
        :param http_client: An :class:`HTTPClient` implementation. Defaults to a global :class:`HTTPXClient`.
        :param query_tags: Tags to associate with the query. See `logging <https://docs.fauna.com/fauna/current/build/logs/query_log/>`_
        :param linearized: If true, unconditionally run the query as strictly serialized. This affects read-only transactions. Transactions which write will always be strictly serialized.
        :param max_contention_retries: The max number of times to retry the query if contention is encountered.
        :param query_timeout: Controls the maximum amount of time (in milliseconds) Fauna will execute your query before marking it failed.
        :param additional_headers: Add/update HTTP request headers for the query. In general, this should not be necessary.
        """

        if endpoint is None:
            self._endpoint = _Environment.EnvFaunaEndpoint()
        else:
            self._endpoint = endpoint

        if secret is None:
            self._auth = _Auth(_Environment.EnvFaunaSecret())
        else:
            self._auth = _Auth(secret)

        self._last_txn_ts = LastTxnTs()

        self._query_tags = {}
        if query_tags is not None:
            self._query_tags.update(query_tags)

        if query_timeout is not None:
            self._query_timeout_ms = query_timeout.total_seconds() * 1000
        else:
            self._query_timeout_ms = None

        self._headers: Dict[str, str] = {
            _Header.AcceptEncoding: "gzip",
            _Header.ContentType: "application/json;charset=utf-8",
            _Header.Driver: "python",
            _Header.DriverEnv: str(_DriverEnvironment()),
        }

        if linearized:
            self._headers[Header.Linearized] = "true"

        if max_contention_retries is not None and max_contention_retries > 0:
            self._headers[Header.MaxContentionRetries] = \
                f"{max_contention_retries}"

        if additional_headers is not None:
            self._headers = {
                **self._headers,
                **additional_headers,
            }

        self._session: HTTPClient

        if http_client is not None:
            self._session = http_client
        else:
            if fauna.global_http_client is None:
                read_timeout: Optional[timedelta] = DefaultHttpReadTimeout
                read_timeout_s: Optional[float] = None
                if read_timeout is not None:
                    read_timeout_s = read_timeout.total_seconds()

                write_timeout_s = DefaultHttpWriteTimeout.total_seconds()
                pool_timeout_s = DefaultHttpPoolTimeout.total_seconds()
                idle_timeout_s = DefaultIdleConnectionTimeout.total_seconds()

                import httpx
                c = HTTPXClient(
                    httpx.Client(
                        http1=False,
                        http2=True,
                        timeout=httpx.Timeout(
                            connect=DefaultMaxConnections,
                            read=read_timeout_s,
                            write=write_timeout_s,
                            pool=pool_timeout_s,
                        ),
                        limits=httpx.Limits(
                            max_connections=DefaultMaxConnections,
                            max_keepalive_connections=DefaultMaxIdleConnections,
                            keepalive_expiry=idle_timeout_s,
                        ),
                    ))
                fauna.global_http_client = c

            self._session = fauna.global_http_client

    def set_last_txn_ts(self, txn_ts: int):
        """
        Set the last timestamp seen by this client.
        This has no effect if earlier than stored timestamp.

        .. WARNING:: This should be used only when coordinating timestamps across
        multiple clients. Moving the timestamp arbitrarily forward into
        the future will cause transactions to stall.

        :param txn_ts: the new transaction time.
        """
        self._last_txn_ts.update_txn_time(txn_ts)

    def get_last_txn_ts(self) -> Optional[int]:
        """
        Get the last timestamp seen by this client.
        :return:
        """
        return self._last_txn_ts.time

    def get_query_timeout(self) -> Optional[timedelta]:
        """
        Get the query timeout for all queries.
        """
        if self._query_timeout_ms is not None:
            return timedelta(milliseconds=self._query_timeout_ms)
        else:
            return None

    def query(
        self,
        fql: QueryBuilder,
        opts: Optional[QueryOptions] = None,
    ) -> QueryResponse:
        """
        Run a query on Fauna.

        :param fql: A string, but will eventually be a query expression.
        :param opts: (Optional) Query Options
        :return: a :class:`QueryResponse`
        :raises NetworkException: HTTP Request failed in transit
        :raises ProtocolException: HTTP error not from Fauna
        :raises ServiceException: Fauna returned an error
        """

        try:
            query = fql.to_query()
        except Exception as e:
            raise ClientError("Failed to evaluate Query") from e

        return self._query(
            "/query/1",
            fql=query,
            opts=opts,
        )

    def _query(
        self,
        path,
        fql: Mapping[str, Any],
        arguments: Optional[Mapping[str, Any]] = None,
        opts: Optional[QueryOptions] = None,
    ) -> QueryResponse:

        headers = self._headers.copy()
        # TODO: should be removed in favor of default (tagged)
        headers[_Header.Format] = "tagged"
        headers[_Header.Authorization] = self._auth.bearer()

        if self._query_timeout_ms is not None:
            headers[Header.TimeoutMs] = str(self._query_timeout_ms)

        headers.update(self._last_txn_ts.request_header)

        query_tags = {}
        if self._query_tags is not None:
            query_tags.update(self._query_tags)

        if opts is not None:
            if opts.linearized is not None:
                headers[Header.Linearized] = str(opts.linearized).lower()
            if opts.max_contention_retries is not None:
                headers[Header.MaxContentionRetries] = \
                    f"{opts.max_contention_retries}"
            if opts.traceparent is not None:
                headers[Header.Traceparent] = opts.traceparent
            if opts.query_timeout is not None:
                headers[Header.TimeoutMs] = \
                    f"{opts.query_timeout.total_seconds() * 1000}"
            if opts.query_tags is not None:
                query_tags.update(opts.query_tags)
            if opts.additional_headers is not None:
                headers.update(opts.additional_headers)

        if len(query_tags) > 0:
            headers[Header.Tags] = urllib.parse.urlencode(query_tags)

        data: dict[str, Any] = {
            "query": fql,
            "arguments": arguments or {},
        }

        with self._session.request(
                method="POST",
                url=self._endpoint + path,
                headers=headers,
                data=data,
        ) as response:
            response_json = response.json()
            headers = response.headers()
            status_code = response.status_code()

            if status_code > 399:
                Client._handle_error(response_json, status_code)

            if "txn_ts" in response_json:
                self.set_last_txn_ts(int(response_json["txn_ts"]))

            return QueryResponse(response_json, headers, status_code)

    @staticmethod
    def _handle_error(response_json: Any, status_code: int):
        if "error" not in response_json:
            raise ProtocolError(
                status_code,
                "Unexpected response",
                response_json,
            )

        err = ServiceError(
            status_code,
            response_json["error"]["code"],
            response_json["error"]["message"],
            response_json["summary"] if "summary" in response_json else "",
        )
        if status_code == 400:
            if err.code is not None:
                raise QueryCheckError(
                    err.status_code,
                    err.code,
                    err.message,
                    err.summary,
                )

            raise QueryRuntimeError(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        elif status_code == 401:
            raise AuthenticationError(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        elif status_code == 403:
            raise AuthorizationError(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        elif status_code == 429:
            raise ThrottlingException(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        elif status_code == 440:
            raise QueryTimeoutException(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        elif status_code == 500:
            raise ServiceInternalError(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        elif status_code == 503:
            raise ServiceTimeoutError(
                err.status_code,
                err.code,
                err.message,
                err.summary,
            )
        else:
            raise err
