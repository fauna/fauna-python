import typing
from time import time

# python3
from urllib.parse import urlencode

import httpx

from httpx._decoders import (
    ByteChunker, )

from httpx._exceptions import (
    StreamClosed,
    StreamConsumed,
    ReadError,
    WriteError,
    request_context,
)
from httpx._types import (
    SyncByteStream, )

from faunadb._json import parse_json_or_none, stream_content_to_json, to_json
from faunadb.request_result import RequestResult
import faunadb.client

from .errors import StreamError
from .events import Error, parse_stream_request_result_or_none

VALID_FIELDS = {"diff", "prev", "document", "action", "index"}


class Connection(object):
    """
    The internal stream client connection interface.
    This class handles the network side of a stream
    subscription.
    """

    def __init__(self, client: 'faunadb.client.FaunaClient', expression,
                 options):
        self._client = client
        self.options = options
        self.conn = None
        self._fields = None
        if isinstance(self.options, dict):
            self._fields = self.options.get("fields", None)
        elif hasattr(self.options, "fields"):
            self._fields = self.options.field
        if isinstance(self._fields, list):
            union = set(self._fields).union(VALID_FIELDS)
            if union != VALID_FIELDS:
                raise Exception("Valid fields options are %s, provided %s." %
                                (VALID_FIELDS, self._fields))
        self._state = "idle"
        self._query = expression
        self._data = to_json(expression).encode()
        try:
            base_url = f"{self._client.scheme}://{self._client.domain}:{self._client.port}"
            self.conn = httpx.Client(
                http2=True,
                http1=False,
                base_url=base_url,
                timeout=None,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=None,
                ),
            )

        except Exception as e:
            raise StreamError(e)

    def close(self):
        """
        Closes the stream subscription by aborting its underlying http request.
        """
        if self.conn is None:
            raise StreamError('Cannot close inactive stream subscription.')
        self._state = 'closing'
        self.conn.close()
        self._state = 'closed'

    def subscribe(self, on_event):
        """Initiates the stream subscription."""
        if self._state != "idle":
            raise StreamError('Stream subscription already started.')
        try:
            self._state = 'connecting'
            headers = self._client.session.headers
            headers["Authorization"] = self._client.auth.auth_header()
            if self._client._query_timeout_ms is not None:
                headers["X-Query-Timeout"] = str(
                    self._client._query_timeout_ms)
            headers["X-Last-Seen-Txn"] = str(self._client.get_last_txn_time())
            start_time = time()
            url_params = ''
            if isinstance(self._fields, list):
                url_params = "?%s" % (urlencode(
                    {'fields': ",".join(self._fields)}))
            stream = self.conn.stream("POST",
                                      "/stream%s" % (url_params),
                                      content=self._data,
                                      headers=dict(headers))
            self._state = 'open'
            with stream as stream_response:
                self._event_loop(stream_response, on_event, start_time)
        except Exception as e:
            if callable(on_event):
                on_event(Error(e), None)

    def _event_loop(
        self,
        stream_response: httpx.Response,
        on_event,
        start_time,
    ):
        if 'x-txn-time' in stream_response.headers:
            self._client.sync_last_txn_time(
                int(stream_response.headers['x-txn-time']))
        try:
            buffer = ''
            for push in self.__httpx_iter_bytes(stream_response):
                try:
                    chunk = push.decode()
                    buffer += chunk
                except:
                    continue

                result = stream_content_to_json(buffer)
                buffer = result["buffer"]

                for value in result["values"]:
                    request_result = self._stream_chunk_to_request_result(
                        stream_response,
                        value["raw"],
                        value["content"],
                        start_time,
                        time(),
                    )
                    event = parse_stream_request_result_or_none(request_result)

                    if event is not None and hasattr(event, 'txn'):
                        self._client.sync_last_txn_time(int(event.txn))
                    on_event(event, request_result)
                    if self._client.observer is not None:
                        self._client.observer(request_result)
        except Exception as e:
            self.error = e
            self.close()
            on_event(Error(e), None)

    def _stream_chunk_to_request_result(
        self,
        response,
        raw,
        content,
        start_time,
        end_time,
    ):
        """ Converts a stream chunk to a RequestResult. """
        return RequestResult(
            "POST",
            "/stream",
            self._query,
            self._data,
            raw,
            content,
            None,
            response.headers,
            start_time,
            end_time,
        )

    # copy/pasted from here https://github.com/encode/httpx/blob/2d37321842c566b1fd81f9627ab4072064286d16/httpx/_models.py#L808
    # then edited.  The actual_self = self dance is to keep the code below as similar as possible to above
    # The reason this is here is to workaround two behaviors of the upstream implementation:
    # bad behavior 1 -- the stream is closed after all the chunks are decoded -- https://github.com/encode/httpx/blob/2d37321842c566b1fd81f9627ab4072064286d16/httpx/_models.py#L889
    # bad behavior 2 -- when the stream is closed from the client side, errors which occur when attempting to recv or sendv the underlying socket will bubble up from the wrong part of the codebase which complictes handling of similar errors should they occur in abnormal circumstances.  See comments in __httpx_iter_raw for more
    def __httpx_iter_bytes(
            self,
            response,
            chunk_size: typing.Optional[int] = None) -> typing.Iterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, and brotli encoded responses.
        """
        actual_self = self
        self = response
        if hasattr(self, "_content"):
            chunk_size = len(
                self._content) if chunk_size is None else chunk_size
            for i in range(0, len(self._content), max(chunk_size, 1)):
                yield self._content[i:i + chunk_size]
        else:
            decoder = self._get_content_decoder()
            chunker = ByteChunker(chunk_size=chunk_size)
            with request_context(request=self._request):
                for raw_bytes in actual_self.__httpx_iter_raw(self):
                    decoded = decoder.decode(raw_bytes)
                    for chunk in chunker.decode(decoded):
                        yield chunk
                decoded = decoder.flush()
                for chunk in chunker.decode(decoded):
                    yield chunk  # pragma: no cover
                for chunk in chunker.flush():
                    yield chunk

    # copy/pasted from here https://github.com/encode/httpx/blob/2d37321842c566b1fd81f9627ab4072064286d16/httpx/_models.py#L863
    # then edited.  The actual_self = self dance is to keep the code below as similar as possible to above
    def __httpx_iter_raw(
            self,
            response,
            chunk_size: typing.Optional[int] = None) -> typing.Iterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        actual_self = self
        self = response
        if self.is_stream_consumed:
            raise StreamConsumed()
        if self.is_closed:
            raise StreamClosed()
        if not isinstance(self.stream, SyncByteStream):
            raise RuntimeError(
                "Attempted to call a sync iterator on an async stream.")

        self.is_stream_consumed = True
        self._num_bytes_downloaded = 0
        chunker = ByteChunker(chunk_size=chunk_size)

        with request_context(request=self._request):
            try:
                for raw_stream_bytes in self.stream:
                    self._num_bytes_downloaded += len(raw_stream_bytes)
                    for chunk in chunker.decode(raw_stream_bytes):
                        yield chunk
            except (ReadError, WriteError) as e:
                # FAUNA_EDIT:
                # add special case error handling for ReadError and WriteError which occur after the application has tried to close the stream.
                # These errors result from the fact that the underlying connection infrastructure (eg os socket) is torn down _before_ the decoder loop is exited
                # ReadError: https://github.com/encode/httpcore/blob/a2f86caa0f230701466e1649c934a87c4dc293f8/httpcore/backends/sync.py#L28 --
                # WriteError: https://github.com/encode/httpcore/blob/7eb20224833b8165d0945d08ac8f714ccb6750b9/httpcore/backends/sync.py#L38 --
                if actual_self._state == "closed":
                    pass
                elif actual_self._state == "closing":
                    pass
                else:
                    raise e

        for chunk in chunker.flush():
            yield chunk
        # FAUNA_EDIT:
        # we don't want to close the connection after decoding a response from the stream ...
        # self.close()