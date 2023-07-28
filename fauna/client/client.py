from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Mapping, Optional, List

import fauna
from fauna.errors import AuthenticationError, ClientError, ProtocolError, ServiceError, AuthorizationError, \
    ServiceInternalError, ServiceTimeoutError, ThrottlingError, QueryTimeoutError, QueryRuntimeError, \
    QueryCheckError, AbortError, InvalidRequestError
from fauna.client.headers import _DriverEnvironment, _Header, _Auth, Header
from fauna.http.http_client import HTTPClient
from fauna.query import Query, Page, fql
from fauna.client.utils import _Environment, LastTxnTs
from fauna.encoding import FaunaEncoder, FaunaDecoder
from fauna.encoding import QuerySuccess, ConstraintFailure, QueryTags, QueryStats

DefaultHttpConnectTimeout = timedelta(seconds=5)
DefaultHttpReadTimeout: Optional[timedelta] = None
DefaultHttpWriteTimeout = timedelta(seconds=5)
DefaultHttpPoolTimeout = timedelta(seconds=5)
DefaultIdleConnectionTimeout = timedelta(seconds=5)
DefaultQueryTimeout = timedelta(seconds=5)
DefaultClientBufferTimeout = timedelta(seconds=5)
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
  query_timeout: Optional[timedelta] = DefaultQueryTimeout
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
      typecheck: Optional[bool] = None,
      additional_headers: Optional[Dict[str, str]] = None,
      query_timeout: Optional[timedelta] = DefaultQueryTimeout,
      client_buffer_timeout: Optional[timedelta] = DefaultClientBufferTimeout,
      http_read_timeout: Optional[timedelta] = DefaultHttpReadTimeout,
      http_write_timeout: Optional[timedelta] = DefaultHttpWriteTimeout,
      http_connect_timeout: Optional[timedelta] = DefaultHttpConnectTimeout,
      http_pool_timeout: Optional[timedelta] = DefaultHttpPoolTimeout,
      http_idle_timeout: Optional[timedelta] = DefaultIdleConnectionTimeout,
  ):
    """Initializes a Client.

        :param endpoint: The Fauna Endpoint to use. Defaults to https://db.fauna.com, or the `FAUNA_ENDPOINT` env variable.
        :param secret: The Fauna Secret to use. Defaults to empty, or the `FAUNA_SECRET` env variable.
        :param http_client: An :class:`HTTPClient` implementation. Defaults to a global :class:`HTTPXClient`.
        :param query_tags: Tags to associate with the query. See `logging <https://docs.fauna.com/fauna/current/build/logs/query_log/>`_
        :param linearized: If true, unconditionally run the query as strictly serialized. This affects read-only transactions. Transactions which write will always be strictly serialized.
        :param max_contention_retries: The max number of times to retry the query if contention is encountered.
        :param typecheck: Enable or disable typechecking of the query before evaluation. If not set, Fauna will use the value of the "typechecked" flag on the database configuration.
        :param additional_headers: Add/update HTTP request headers for the query. In general, this should not be necessary.
        :param query_timeout: Controls the maximum amount of time Fauna will execute your query before marking it failed, default is :py:data:`DefaultQueryTimeout`.
        :param client_buffer_timeout: Time in milliseconds beyond query_timeout at which the client will abort a request if it has not received a response. The default is :py:data:`DefaultClientBufferTimeout`, which should account for network latency for most clients. The value must be greater than zero. The closer to zero the value is, the more likely the client is to abort the request before the server can report a legitimate response or error.
        :param http_read_timeout: Set HTTP Read timeout, default is :py:data:`DefaultHttpReadTimeout`.
        :param http_write_timeout: Set HTTP Write timeout, default is :py:data:`DefaultHttpWriteTimeout`.
        :param http_connect_timeout: Set HTTP Connect timeout, default is :py:data:`DefaultHttpConnectTimeout`.
        :param http_pool_timeout: Set HTTP Pool timeout, default is :py:data:`DefaultHttpPoolTimeout`.
        :param http_idle_timeout: Set HTTP Idle timeout, default is :py:data:`DefaultIdleConnectionTimeout`.
        """

    self._set_endpoint(endpoint)

    if secret is None:
      self._auth = _Auth(_Environment.EnvFaunaSecret())
    else:
      self._auth = _Auth(secret)

    self._last_txn_ts = LastTxnTs()

    self._query_tags = {}
    if query_tags is not None:
      self._query_tags.update(query_tags)

    if query_timeout is not None:
      self._query_timeout_ms = int(query_timeout.total_seconds() * 1000)
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
        timeout_s: Optional[float] = None
        if query_timeout is not None and client_buffer_timeout is not None:
          timeout_s = (query_timeout + client_buffer_timeout).total_seconds()
        read_timeout_s: Optional[float] = None
        if http_read_timeout is not None:
          read_timeout_s = http_read_timeout.total_seconds()

        write_timeout_s: Optional[float] = http_write_timeout.total_seconds(
        ) if http_write_timeout is not None else None
        connect_timeout_s: Optional[float] = http_connect_timeout.total_seconds(
        ) if http_connect_timeout is not None else None
        pool_timeout_s: Optional[float] = http_pool_timeout.total_seconds(
        ) if http_pool_timeout is not None else None
        idle_timeout_s: Optional[float] = http_idle_timeout.total_seconds(
        ) if http_idle_timeout is not None else None

        import httpx
        from fauna.http.httpx_client import HTTPXClient
        c = HTTPXClient(
            httpx.Client(
                http1=False,
                http2=True,
                timeout=httpx.Timeout(
                    timeout=timeout_s,
                    connect=connect_timeout_s,
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

  def paginate(
      self,
      fql: Query,
      opts: Optional[QueryOptions] = None,
  ) -> "QueryIterator":
    """
        Run a query on Fauna and returning an iterator of results. If the query
        returns a Page, the iterator will fetch additional Pages until the
        after token is null.

        :param fql: A Query
        :param opts: (Optional) Query Options

        :return: a :class:`QueryResponse`

        :raises NetworkError: HTTP Request failed in transit
        :raises ProtocolError: HTTP error not from Fauna
        :raises ServiceError: Fauna returned an error
        :raises ValueError: Encoding and decoding errors
        :raises TypeError: Invalid param types
        """

    if not isinstance(fql, Query):
      err_msg = f"'fql' must be a Query but was a {type(fql)}. You can build a " \
                 f"Query by calling fauna.fql()"
      raise TypeError(err_msg)

    return QueryIterator(self, fql, opts)

  def query(
      self,
      fql: Query,
      opts: Optional[QueryOptions] = None,
  ) -> QuerySuccess:
    """
        Run a query on Fauna.

        :param fql: A Query
        :param opts: (Optional) Query Options

        :return: a :class:`QueryResponse`

        :raises NetworkError: HTTP Request failed in transit
        :raises ProtocolError: HTTP error not from Fauna
        :raises ServiceError: Fauna returned an error
        :raises ValueError: Encoding and decoding errors
        :raises TypeError: Invalid param types
        """

    if not isinstance(fql, Query):
      err_msg = f"'fql' must be a Query but was a {type(fql)}. You can build a " \
                 f"Query by calling fauna.fql()"
      raise TypeError(err_msg)

    try:
      encoded_query: Mapping[str, Any] = FaunaEncoder.encode(fql)
    except Exception as e:
      raise ClientError("Failed to encode Query") from e

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
      headers[Header.QueryTimeoutMs] = str(self._query_timeout_ms)

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
        timeout_ms = f"{int(opts.query_timeout.total_seconds() * 1000)}"
        headers[Header.QueryTimeoutMs] = timeout_ms
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

      dec: Any = FaunaDecoder.decode(response_json)

      if status_code > 399:
        self._handle_error(dec, status_code)

      if "txn_ts" in dec:
        self.set_last_txn_ts(int(response_json["txn_ts"]))

      stats = QueryStats(dec["stats"]) if "stats" in dec else None
      summary = dec["summary"] if "summary" in dec else None
      query_tags = QueryTags.decode(
          dec["query_tags"]) if "query_tags" in dec else None
      txn_ts = dec["txn_ts"] if "txn_ts" in dec else None
      schema_version = dec["schema_version"] if "schema_version" in dec else None
      traceparent = headers.get("traceparent", None)
      static_type = dec["static_type"] if "static_type" in dec else None

      return QuerySuccess(
          data=dec["data"],
          query_tags=query_tags,
          static_type=static_type,
          stats=stats,
          summary=summary,
          traceparent=traceparent,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )

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
          f"Response is in an unknown format: \n{response_json}",
      )

  def _handle_error(self, body: Any, status_code: int):
    err = body["error"]
    code = err["code"]
    message = err["message"]

    query_tags = QueryTags.decode(
        body["query_tags"]) if "query_tags" in body else None
    stats = QueryStats(body["stats"]) if "stats" in body else None
    txn_ts = body["txn_ts"] if "txn_ts" in body else None
    schema_version = body["schema_version"] if "schema_version" in body else None
    summary = body["summary"] if "summary" in body else None

    constraint_failures: Optional[List[ConstraintFailure]] = None
    if "constraint_failures" in err:
      constraint_failures = [
          ConstraintFailure(
              message=cf["message"],
              name=cf["name"] if "name" in cf else None,
              paths=cf["paths"] if "paths" in cf else None,
          ) for cf in err["constraint_failures"]
      ]

    if status_code == 400:
      if code == "invalid_query":
        raise QueryCheckError(
            status_code=status_code,
            code=code,
            message=message,
            summary=summary,
            constraint_failures=constraint_failures,
            query_tags=query_tags,
            stats=stats,
            txn_ts=txn_ts,
            schema_version=schema_version,
        )
      elif code == "invalid_request":
        raise InvalidRequestError(
            status_code=status_code,
            code=code,
            message=message,
            summary=summary,
            constraint_failures=constraint_failures,
            query_tags=query_tags,
            stats=stats,
            txn_ts=txn_ts,
            schema_version=schema_version,
        )
      elif code == "abort":
        abort = err["abort"] if "abort" in err else None
        raise AbortError(
            status_code=status_code,
            code=code,
            message=message,
            summary=summary,
            abort=abort,
            constraint_failures=constraint_failures,
            query_tags=query_tags,
            stats=stats,
            txn_ts=txn_ts,
            schema_version=schema_version,
        )

      else:
        raise QueryRuntimeError(
            status_code=status_code,
            code=code,
            message=message,
            summary=summary,
            constraint_failures=constraint_failures,
            query_tags=query_tags,
            stats=stats,
            txn_ts=txn_ts,
            schema_version=schema_version,
        )
    elif status_code == 401:
      raise AuthenticationError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )
    elif status_code == 403:
      raise AuthorizationError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )
    elif status_code == 429:
      raise ThrottlingError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )
    elif status_code == 440:
      raise QueryTimeoutError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )
    elif status_code == 500:
      raise ServiceInternalError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )
    elif status_code == 503:
      raise ServiceTimeoutError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )
    else:
      raise ServiceError(
          status_code=status_code,
          code=code,
          message=message,
          summary=summary,
          constraint_failures=constraint_failures,
          query_tags=query_tags,
          stats=stats,
          txn_ts=txn_ts,
          schema_version=schema_version,
      )

  def _set_endpoint(self, endpoint):
    if endpoint is None:
      endpoint = _Environment.EnvFaunaEndpoint()

    if endpoint[-1:] == "/":
      endpoint = endpoint[:-1]

    self._endpoint = endpoint


class QueryIterator:
  """A class to provider an iterator on top of Fauna queries."""

  def __init__(self,
               client: Client,
               fql: Query,
               opts: Optional[QueryOptions] = None):
    """Initializes the QueryIterator

        :param fql: A Query
        :param opts: (Optional) Query Options

        :raises TypeError: Invalid param types
        """
    if not isinstance(client, Client):
      err_msg = f"'client' must be a Client but was a {type(client)}. You can build a " \
                  f"Client by calling fauna.client.Client()"
      raise TypeError(err_msg)

    if not isinstance(fql, Query):
      err_msg = f"'fql' must be a Query but was a {type(fql)}. You can build a " \
                 f"Query by calling fauna.fql()"
      raise TypeError(err_msg)

    self.client = client
    self.fql = fql
    self.opts = opts

  def __iter__(self) -> Iterator:
    return self.iter()

  def iter(self) -> Iterator:
    """
        A generator function that immediately fetches and yields the results of
        the stored query. Yields additional pages on subsequent iterations if
        they exist
        """

    cursor = None
    initial_response = self.client.query(self.fql, self.opts)

    if isinstance(initial_response.data, Page):
      cursor = initial_response.data.after
      yield initial_response.data.data

      while cursor is not None:
        next_response = self.client.query(
            fql("Set.paginate(${after})", after=cursor), self.opts)
        # TODO: `Set.paginate` does not yet return a `@set` tagged value
        #       so we will get back a plain object that might not have
        #       an after property.
        cursor = next_response.data.get("after")
        yield next_response.data.get("data")

    else:
      yield [initial_response.data]

  def flatten(self) -> Iterator:
    """
        A generator function that immediately fetches and yields the results of
        the stored query. Yields each item individually, rather than a whole
        Page at a time. Fetches additional pages as required if they exist.
        """

    for page in self.iter():
      for item in page:
        yield item
