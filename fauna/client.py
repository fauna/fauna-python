from datetime import timedelta
from typing import Any, Optional, Mapping

import fauna
from fauna.headers import _DriverEnvironment, _Header, _Auth, Header
from fauna.http_client import HTTPClient, HTTPXClient
from fauna.utils import _Environment, _LastTxnTime

DefaultHttpConnectTimeout = timedelta(seconds=5)
DefaultHttpReadTimeout = None
DefaultHttpWriteTimeout = timedelta(seconds=5)
DefaultHttpPoolTimeout = timedelta(seconds=5)
DefaultIdleConnectionTimeout = timedelta(seconds=5)
DefaultMaxConnections = 20
DefaultMaxIdleConnections = 20


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

                if query_timeout is not None:
                    read_timeout_buffer: timedelta = timedelta(seconds=2)
                    read_timeout = query_timeout + read_timeout_buffer

                import httpx
                c = HTTPXClient(
                    httpx.Client(
                        http1=False,
                        http2=True,
                        timeout=httpx.Timeout(
                            connect=DefaultMaxConnections,
                            read=read_timeout.total_seconds() *
                            1000 if read_timeout is not None else None,
                            write=DefaultHttpWriteTimeout.total_seconds() *
                            1000,
                            pool=DefaultHttpPoolTimeout.total_seconds() * 1000,
                        ),
                        limits=httpx.Limits(
                            max_connections=DefaultMaxConnections,
                            max_keepalive_connections=DefaultMaxIdleConnections,
                            keepalive_expiry=DefaultIdleConnectionTimeout.
                            total_seconds() * 1000,
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

    def get_last_transaction_time(self) -> Optional[str]:
        """
        Get the last timestamp seen by this client.
        :return:
        """
        return self._last_txn_time.time

    def get_query_timeout(self) -> Optional[timedelta]:
        """
        Get the query timeout for all queries.
        """
        return timedelta(milliseconds=self._query_timeout_ms
                         ) if self._query_timeout_ms is not None else None

    def query(
            self,
            fql: str,  # TODO(lucas) use a home-baked fql expression type
    ):
        """
        Use the Fauna query API.

        :param fql: A string, but will eventually be a query expression.
        :return: Response. TODO(lucas): refine contract
        """
        return self._execute(
            "/query/1",
            fql=fql,
        )

    def _execute(
            self,
            path,
            fql: str,  # TODO(lucas) use a home-baked fql expression type
    ):

        headers = self._headers.copy()
        headers[_Header.Authorization] = self._auth.bearer()

        if self._query_timeout_ms is not None:
            headers[Header.TimeoutMs] = str(self._query_timeout_ms)

        if self.track_last_transaction_time:
            headers.update(self._last_txn_time.request_header)

        data: dict[str, Any] = {
            "typecheck": False,
            "query": fql,
            "arguments": {}
        }

        response = self.session.request(
            method="POST",
            url=self.endpoint + path,
            headers=headers,
            data=data,
        )

        if self.track_last_transaction_time:
            x_txn_time_headers = [
                item for item in response.headers() if item[0] == "X-Txn-Time"
            ]
            if len(x_txn_time_headers) == 1:
                new_txn_time = int(x_txn_time_headers[0][1])
                self.sync_last_txn_time(new_txn_time)

        return response
