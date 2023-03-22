from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, List

import fauna
from fauna.errors import AuthenticationError, ClientError, ProtocolError, ServiceError, AuthorizationError, \
    ServiceInternalError, ServiceTimeoutError, ThrottlingError, QueryTimeoutError, QueryRuntimeError, \
    QueryCheckError
from fauna.client.headers import _DriverEnvironment, _Header, _Auth, Header
from fauna.http.http_client import HTTPClient
from fauna.query.query_builder import QueryInterpolation
from fauna.client.utils import _Environment, LastTxnTs
from fauna.encoding import FaunaEncoder
from fauna.client.wire_protocol import QuerySuccess, ConstraintFailure, QueryInfo, QueryTags

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
    * typecheck - Enable or disable typechecking of the query before evaluation. If not set, the value configured on the Client will be used. If neither is set, Fauna will use the value of the "typechecked" flag on the database configuration.
    * additional_headers - Add/update HTTP request headers for the query. In general, this should not be necessary.
    """

    linearized: Optional[bool] = None
    max_contention_retries: Optional[int] = None
    query_timeout: Optional[timedelta] = None
    query_tags: Optional[Mapping[str, str]] = None
    traceparent: Optional[str] = None
    typecheck: Optional[bool] = None
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
        typecheck: Optional[bool] = None,
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
        :param typecheck: Enable or disable typechecking of the query before evaluation. If not set, Fauna will use the value of the "typechecked" flag on the database configuration.
        :param additional_headers: Add/update HTTP request headers for the query. In general, this should not be necessary.
        """

        if endpoint is None:
            self._endpoint = _Environment.EnvFaunaEndpoint()
        else:
            self._endpoint = endpoint

        print(f"endpoint set to {self._endpoint}")

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

        if typecheck is not None:
            self._headers[Header.Typecheck] = str(typecheck).lower()

        if linearized is not None:
            self._headers[Header.Linearized] = str(linearized).lower()

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
                from fauna.http.httpx_client import HTTPXClient
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
        fql: QueryInterpolation,
        opts: Optional[QueryOptions] = None,
    ) -> QuerySuccess:
        """
        Run a query on Fauna.

        :param fql: A string, but will eventually be a query expression.
        :param opts: (Optional) Query Options

        :return: a :class:`QueryResponse`

        :raises NetworkError: HTTP Request failed in transit
        :raises ProtocolError: HTTP error not from Fauna
        :raises ServiceError: Fauna returned an error
        :raises ValueError: Encoding and decoding errors
        """

        try:
            encoded_query: Mapping[str, Any] = FaunaEncoder.encode(fql)
        except Exception as e:
            raise ClientError("Failed to evaluate Query") from e

        return self._query(
            "/query/1",
            fql=encoded_query,
            opts=opts,
        )

    def _query(
        self,
        path: str,
        fql: Mapping[str, Any],
        arguments: Optional[Mapping[str, Any]] = None,
        opts: Optional[QueryOptions] = None,
    ) -> QuerySuccess:

        headers = self._headers.copy()
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
                timeout_ms = f"{opts.query_timeout.total_seconds() * 1000}"
                headers[Header.TimeoutMs] = timeout_ms
            if opts.query_tags is not None:
                query_tags.update(opts.query_tags)
            if opts.typecheck is not None:
                headers[Header.Typecheck] = str(opts.typecheck).lower()
            if opts.additional_headers is not None:
                headers.update(opts.additional_headers)

        if len(query_tags) > 0:
            headers[Header.Tags] = QueryTags.encode(query_tags)

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

            self._check_protocol(response_json, status_code)

            if status_code > 399:
                self._handle_error(response_json, status_code)

            if "txn_ts" in response_json:
                self.set_last_txn_ts(int(response_json["txn_ts"]))

            return QuerySuccess(response_json, headers)

    def _check_protocol(self, response_json: Any, status_code):
        # TODO: Logic to validate wire protocol belongs elsewhere.
        should_raise = False

        # check for QuerySuccess
        if status_code <= 399 and "data" not in response_json:
            should_raise = True

        # check for QueryFailure
        if status_code > 399:
            if "error" not in response_json:
                should_raise = True
            else:
                e = response_json["error"]
                if "code" not in e or "message" not in e:
                    should_raise = True

        if should_raise:
            raise ProtocolError(
                status_code,
                "Unexpected response",
                f"Response is in an unknown format: \n{response_json}",
            )

    def _handle_error(self, body: Any, status_code: int):
        err = body["error"]
        code = err["code"]
        message = err["message"]
        constraint_failures: Optional[List[ConstraintFailure]] = None
        query_info = QueryInfo(
            query_tags=body["query_tags"] if "query_tags" in body else None,
            stats=body["stats"] if "stats" in body else None,
            txn_ts=body["txn_ts"] if "txn_ts" in body else None,
            summary=body["summary"] if "summary" in body else None,
        )

        if "constraint_failures" in err:
            constraint_failures = [
                ConstraintFailure(
                    message=cf["message"],
                    name=cf["name"] if "name" in cf else None,
                    paths=cf["paths"] if "paths" in cf else None,
                ) for cf in err["constraint_failures"]
            ]

        if status_code == 400:
            query_check_codes = [
                "invalid_function_definition", "invalid_identifier",
                "invalid_query", "invalid_syntax", "invalid_type"
            ]
            if code in query_check_codes:
                raise QueryCheckError(
                    status_code,
                    code,
                    message,
                    query_info,
                )
            else:
                raise QueryRuntimeError(
                    status_code,
                    code,
                    message,
                    query_info,
                    constraint_failures,
                )
        elif status_code == 401:
            raise AuthenticationError(
                status_code,
                code,
                message,
                query_info,
            )
        elif status_code == 403:
            raise AuthorizationError(
                status_code,
                code,
                message,
                query_info,
            )
        elif status_code == 429:
            raise ThrottlingError(
                status_code,
                code,
                message,
                query_info,
            )
        elif status_code == 440:
            raise QueryTimeoutError(
                status_code,
                code,
                message,
                query_info,
            )
        elif status_code == 500:
            raise ServiceInternalError(
                status_code,
                code,
                message,
                query_info,
            )
        elif status_code == 503:
            raise ServiceTimeoutError(
                status_code,
                code,
                message,
                query_info,
            )
        else:
            raise ServiceError(
                status_code,
                code,
                message,
                query_info,
            )
