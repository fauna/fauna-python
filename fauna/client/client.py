import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterator, Mapping, Optional, Union, List

import fauna
from fauna.client.headers import _DriverEnvironment, _Header, _Auth, Header
from fauna.client.retryable import Retryable
from fauna.client.utils import _Environment, LastTxnTs
from fauna.encoding import FaunaEncoder, FaunaDecoder
from fauna.encoding import QuerySuccess, QueryTags, QueryStats
from fauna.errors import FaunaError, ClientError, ProtocolError, \
  RetryableFaunaException, NetworkError
from fauna.http.http_client import HTTPClient
from fauna.query import EventSource, Query, Page, fql

logger = logging.getLogger("fauna")

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


@dataclass
class StreamOptions:
  """
    A dataclass representing options available for a stream.

    * max_attempts - The maximum number of times to attempt a stream query when a retryable exception is thrown.
    * max_backoff - The maximum backoff in seconds for an individual retry.
    * start_ts - The starting timestamp of the stream, exclusive. If set, Fauna will return events starting after
    the timestamp.
    * cursor - The starting event cursor, exclusive. If set, Fauna will return events starting after the cursor.
    * status_events - Indicates if stream should include status events. Status events are periodic events that
    update the client with the latest valid timestamp (in the event of a dropped connection) as well as metrics
    about the cost of maintaining the stream other than the cost of the received events.
    """

  max_attempts: Optional[int] = None
  max_backoff: Optional[int] = None
  start_ts: Optional[int] = None
  cursor: Optional[str] = None
  status_events: bool = False


@dataclass
class FeedOptions:
  """
    A dataclass representing options available for an event feed.

    * max_attempts - The maximum number of times to attempt an event feed query when a retryable exception is thrown.
    * max_backoff - The maximum backoff in seconds for an individual retry.
    * query_timeout - Controls the maximum amount of time Fauna will execute a query before returning a page of events.
    * start_ts - The starting timestamp of the event feed, exclusive. If set, Fauna will return events starting after
    the timestamp.
    * cursor - The starting event cursor, exclusive. If set, Fauna will return events starting after the cursor.
    * page_size - Maximum number of events returned per page. Must be in the
    range 1 to 16000 (inclusive). Defaults to 16.
    """
  max_attempts: Optional[int] = None
  max_backoff: Optional[int] = None
  query_timeout: Optional[timedelta] = None
  page_size: Optional[int] = None
  start_ts: Optional[int] = None
  cursor: Optional[str] = None


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
      max_attempts: int = 3,
      max_backoff: int = 20,
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
        :param max_attempts: The maximum number of times to attempt a query when a retryable exception is thrown. Defaults to 3.
        :param max_backoff: The maximum backoff in seconds for an individual retry. Defaults to 20.
        """

    self._set_endpoint(endpoint)
    self._max_attempts = max_attempts
    self._max_backoff = max_backoff

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
                http1=True,
                http2=False,
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
            ), logger)
        fauna.global_http_client = c

      self._session = fauna.global_http_client

  def close(self):
    self._session.close()
    if self._session == fauna.global_http_client:
      fauna.global_http_client = None

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
        after token is null. Each call for a page will be retried with exponential
        backoff up to the max_attempts set in the client's retry policy in the
        event of a 429 or 502.

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
        Run a query on Fauna. A query will be retried max_attempt times with exponential backoff
        up to the max_backoff in the event of a 429.

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

    retryable = Retryable[QuerySuccess](
        self._max_attempts,
        self._max_backoff,
        self._query,
        "/query/1",
        fql=encoded_query,
        opts=opts,
    )

    r = retryable.run()
    r.response.stats.attempts = r.attempts
    return r.response

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
      status_code = response.status_code()
      response_json = response.json()
      headers = response.headers()

      self._check_protocol(response_json, status_code)

      dec: Any = FaunaDecoder.decode(response_json)

      if status_code > 399:
        FaunaError.parse_error_and_throw(dec, status_code)

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

  def stream(
      self,
      fql: Union[EventSource, Query],
      opts: StreamOptions = StreamOptions()
  ) -> "StreamIterator":
    """
        Opens a Stream in Fauna and returns an iterator that consume Fauna events.

        :param fql: An EventSource or a Query that returns an EventSource.
        :param opts: (Optional) Stream Options.

        :return: a :class:`StreamIterator`

        :raises ClientError: Invalid options provided
        :raises NetworkError: HTTP Request failed in transit
        :raises ProtocolError: HTTP error not from Fauna
        :raises ServiceError: Fauna returned an error
        :raises ValueError: Encoding and decoding errors
        :raises TypeError: Invalid param types
        """

    if isinstance(fql, Query):
      if opts.cursor is not None:
        raise ClientError(
            "The 'cursor' configuration can only be used with an event source.")

      source = self.query(fql).data
    else:
      source = fql

    if not isinstance(source, EventSource):
      err_msg = f"'fql' must be an EventSource, or a Query that returns an EventSource but was a {type(source)}."
      raise TypeError(err_msg)

    headers = self._headers.copy()
    headers[_Header.Format] = "tagged"
    headers[_Header.Authorization] = self._auth.bearer()

    return StreamIterator(self._session, headers, self._endpoint + "/stream/1",
                          self._max_attempts, self._max_backoff, opts, source)

  def feed(
      self,
      source: Union[EventSource, Query],
      opts: FeedOptions = FeedOptions(),
  ) -> "FeedIterator":
    """
        Opens an event feed in Fauna and returns an iterator that consume Fauna events.

        :param source: An EventSource or a Query that returns an EventSource.
        :param opts: (Optional) Event feed options.

        :return: a :class:`FeedIterator`

        :raises ClientError: Invalid options provided
        :raises NetworkError: HTTP Request failed in transit
        :raises ProtocolError: HTTP error not from Fauna
        :raises ServiceError: Fauna returned an error
        :raises ValueError: Encoding and decoding errors
        :raises TypeError: Invalid param types
        """

    if isinstance(source, Query):
      source = self.query(source).data

    if not isinstance(source, EventSource):
      err_msg = f"'source' must be an EventSource, or a Query that returns an EventSource but was a {type(source)}."
      raise TypeError(err_msg)

    headers = self._headers.copy()
    headers[_Header.Format] = "tagged"
    headers[_Header.Authorization] = self._auth.bearer()

    if opts.query_timeout is not None:
      query_timeout_ms = int(opts.query_timeout.total_seconds() * 1000)
      headers[Header.QueryTimeoutMs] = str(query_timeout_ms)
    elif self._query_timeout_ms is not None:
      headers[Header.QueryTimeoutMs] = str(self._query_timeout_ms)

    return FeedIterator(self._session, headers, self._endpoint + "/feed/1",
                        self._max_attempts, self._max_backoff, opts, source)

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

  def _set_endpoint(self, endpoint):
    if endpoint is None:
      endpoint = _Environment.EnvFaunaEndpoint()

    if endpoint[-1:] == "/":
      endpoint = endpoint[:-1]

    self._endpoint = endpoint


class StreamIterator:
  """A class that mixes a ContextManager and an Iterator so we can detected retryable errors."""

  def __init__(self, http_client: HTTPClient, headers: Dict[str, str],
               endpoint: str, max_attempts: int, max_backoff: int,
               opts: StreamOptions, source: EventSource):
    self._http_client = http_client
    self._headers = headers
    self._endpoint = endpoint
    self._max_attempts = max_attempts
    self._max_backoff = max_backoff
    self._opts = opts
    self._source = source
    self._stream = None
    self.last_ts = None
    self.last_cursor = None
    self._ctx = self._create_stream()

    if opts.start_ts is not None and opts.cursor is not None:
      err_msg = "Only one of 'start_ts' or 'cursor' can be defined in the StreamOptions."
      raise TypeError(err_msg)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, exc_traceback):
    if self._stream is not None:
      self._stream.close()

    self._ctx.__exit__(exc_type, exc_value, exc_traceback)
    return False

  def __iter__(self):
    return self

  def __next__(self):
    if self._opts.max_attempts is not None:
      max_attempts = self._opts.max_attempts
    else:
      max_attempts = self._max_attempts

    if self._opts.max_backoff is not None:
      max_backoff = self._opts.max_backoff
    else:
      max_backoff = self._max_backoff

    retryable = Retryable[Any](max_attempts, max_backoff, self._next_element)
    return retryable.run().response

  def _next_element(self):
    try:
      if self._stream is None:
        try:
          self._stream = self._ctx.__enter__()
        except Exception:
          self._retry_stream()

      if self._stream is not None:
        event: Any = FaunaDecoder.decode(next(self._stream))

        if event["type"] == "error":
          FaunaError.parse_error_and_throw(event, 400)

        self.last_ts = event["txn_ts"]
        self.last_cursor = event.get('cursor')

        if event["type"] == "start":
          return self._next_element()

        if not self._opts.status_events and event["type"] == "status":
          return self._next_element()

        return event

      raise StopIteration
    except NetworkError:
      self._retry_stream()

  def _retry_stream(self):
    if self._stream is not None:
      self._stream.close()

    self._stream = None

    try:
      self._ctx = self._create_stream()
    except Exception:
      pass
    raise RetryableFaunaException

  def _create_stream(self):
    data: Dict[str, Any] = {"token": self._source.token}
    if self.last_cursor is not None:
      data["cursor"] = self.last_cursor
    elif self._opts.cursor is not None:
      data["cursor"] = self._opts.cursor
    elif self._opts.start_ts is not None:
      data["start_ts"] = self._opts.start_ts

    return self._http_client.stream(
        url=self._endpoint, headers=self._headers, data=data)

  def close(self):
    if self._stream is not None:
      self._stream.close()


class FeedPage:

  def __init__(self, events: List[Any], cursor: str, stats: QueryStats):
    self._events = events
    self.cursor = cursor
    self.stats = stats

  def __len__(self):
    return len(self._events)

  def __iter__(self) -> Iterator[Any]:
    for event in self._events:
      if event["type"] == "error":
        FaunaError.parse_error_and_throw(event, 400)
      yield event


class FeedIterator:
  """A class to provide an iterator on top of event feed pages."""

  def __init__(self, http: HTTPClient, headers: Dict[str, str], endpoint: str,
               max_attempts: int, max_backoff: int, opts: FeedOptions,
               source: EventSource):
    self._http = http
    self._headers = headers
    self._endpoint = endpoint
    self._max_attempts = opts.max_attempts or max_attempts
    self._max_backoff = opts.max_backoff or max_backoff
    self._request: Dict[str, Any] = {"token": source.token}
    self._is_done = False

    if opts.start_ts is not None and opts.cursor is not None:
      err_msg = "Only one of 'start_ts' or 'cursor' can be defined in the FeedOptions."
      raise TypeError(err_msg)

    if opts.page_size is not None:
      self._request["page_size"] = opts.page_size

    if opts.cursor is not None:
      self._request["cursor"] = opts.cursor
    elif opts.start_ts is not None:
      self._request["start_ts"] = opts.start_ts

  def __iter__(self) -> Iterator[FeedPage]:
    self._is_done = False
    return self

  def __next__(self) -> FeedPage:
    if self._is_done:
      raise StopIteration

    retryable = Retryable[Any](self._max_attempts, self._max_backoff,
                               self._next_page)
    return retryable.run().response

  def _next_page(self) -> FeedPage:
    with self._http.request(
        method="POST",
        url=self._endpoint,
        headers=self._headers,
        data=self._request,
    ) as response:
      status_code = response.status_code()
      decoded: Any = FaunaDecoder.decode(response.json())

      if status_code > 399:
        FaunaError.parse_error_and_throw(decoded, status_code)

      self._is_done = not decoded["has_next"]
      self._request["cursor"] = decoded["cursor"]

      if "start_ts" in self._request:
        del self._request["start_ts"]

      return FeedPage(decoded["events"], decoded["cursor"],
                      QueryStats(decoded["stats"]))

  def flatten(self) -> Iterator:
    """A generator that yields events instead of pages of events."""
    for page in self:
      for event in page:
        yield event


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
