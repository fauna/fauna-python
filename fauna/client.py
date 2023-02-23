from datetime import timedelta
from typing import Any, Dict, Mapping, Optional

import fauna
from fauna.response import Response, FaunaException
from fauna.headers import _DriverEnvironment, _Header, _Auth, Header
from fauna.http_client import HTTPClient, HTTPXClient
from fauna.utils import _Environment, _LastTxnTime

DefaultHttpConnectTimeout = timedelta(seconds=5)
DefaultHttpReadTimeout: Optional[timedelta] = None
DefaultHttpWriteTimeout = timedelta(seconds=5)
DefaultHttpPoolTimeout = timedelta(seconds=5)
DefaultIdleConnectionTimeout = timedelta(seconds=5)
DefaultMaxConnections = 20
DefaultMaxIdleConnections = 20


class QueryOptions:

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
            self._headers[Header.Tags] = '&'.join(
                [f"{k}={tags[k]}" for k in tags])

        if traceparent is not None:
            self._headers[Header.Traceparent] = traceparent

    def headers(self) -> Dict[str, str]:
        return self._headers


class Client(object):

    def __init__(
        self,
        endpoint: Optional[str] = None,
        secret: Optional[str] = None,
        http_client: Optional[HTTPClient] = None,
        tags: Optional[Mapping[str, str]] = None,
        track_last_transaction_time: bool = True,
        linearized: Optional[bool] = None,
        max_contention_retries: Optional[int] = None,
        query_timeout: Optional[timedelta] = None,
    ):
        if endpoint is None:
            self.endpoint = _Environment.EnvFaunaEndpoint()
        else:
            self.endpoint = endpoint

        if secret is None:
            self._auth = _Auth(_Environment.EnvFaunaSecret())
        else:
            self._auth = _Auth(secret)

        self._last_txn_time = _LastTxnTime()
        self.track_last_transaction_time = track_last_transaction_time
        self.linearized = linearized
        self.max_contention_retries = max_contention_retries
        self.tags = {}
        if tags is not None:
            self.tags.update(tags)

        if query_timeout is not None:
            self._query_timeout_ms = query_timeout.total_seconds() * 1000
        else:
            self._query_timeout_ms = None

        self._headers = {
            _Header.AcceptEncoding: "gzip",
            _Header.ContentType: "application/json;charset=utf-8",
            _Header.Driver: "python",
            _Header.DriverEnv: str(_DriverEnvironment())
        }

        self.session: HTTPClient

        if http_client is not None:
            self.session = http_client
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

            self.session = fauna.global_http_client

    def set_last_transaction_time(self, new_transaction_time: int):
        """
        Set the last timestamp seen by this client.
        This has no effect if earlier than stored timestamp.

        WARNING: This should be used only when coordinating timestamps across
                multiple clients. Moving the timestamp arbitrarily forward into
                the future will cause transactions to stall.

        :param new_transaction_time: the new transaction time.
        """
        self._last_txn_time.update_txn_time(new_transaction_time)

    def get_last_transaction_time(self) -> Optional[int]:
        """
        Get the last timestamp seen by this client.
        :return:
        """
        return self._last_txn_time.time

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
        fql: str,  # TODO(lucas) use a home-baked fql expression type
        opts: Optional[QueryOptions] = None,
    ) -> Response:
        """
        Use the Fauna query API.

        :param fql: A string, but will eventually be a query expression.
        :param opts: (Optional) Query Options
        :return: Response. TODO(lucas): refine contract
        """
        return self._execute(
            "/query/1",
            fql=fql,
            opts=opts,
        )

    def _execute(
        self,
        path,
        fql: str,  # TODO(lucas) use a home-baked fql expression type
        opts: Optional[QueryOptions] = None,
    ) -> Response:
        """
        :raises FaunaException: Fauna returned an error
        """

        headers = self._headers.copy()
        # TODO: should be removed in favor of default (tagged)
        headers["X-Format"] = "simple"
        headers[_Header.Authorization] = self._auth.bearer()

        if self._query_timeout_ms is not None:
            headers[Header.TimeoutMs] = str(self._query_timeout_ms)

        if self.track_last_transaction_time:
            headers.update(self._last_txn_time.request_header)

        if opts is not None:
            for k, v in opts.headers().items():
                headers[k] = v

        data: dict[str, Any] = {
            "query": fql,
            "arguments": {},
        }

        response = self.session.request(
            method="POST",
            url=self.endpoint + path,
            headers=headers,
            data=data,
        )

        if self.track_last_transaction_time:
            if Header.TxnTime in response.headers():
                x_txn_time = response.headers()[Header.TxnTime]
                self.set_last_transaction_time(int(x_txn_time))

        err = response.error()
        if err is not None:
            raise FaunaException(err)

        return Response(response)
