from typing import cast, Any
from time import time

# python3
from urllib.parse import urlencode

import httpx

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

    def __init__(
        self,
        client: 'faunadb.client.FaunaClient',
        expression,
        options,
    ):
        self._client = client
        self._options = options
        self._fields = None
        if isinstance(self._options, dict):
            self._fields = self._options.get("fields", None)
        elif hasattr(self._options, "fields"):
            self._fields = self._options.field
        if isinstance(self._fields, list):
            union = set(self._fields).union(VALID_FIELDS)
            if union != VALID_FIELDS:
                raise Exception("Valid fields options are %s, provided %s." %
                                (VALID_FIELDS, self._fields))
        self._state = "idle"
        self._query = expression
        self._data = to_json(expression).encode()
        try:
            self.conn = client.session

        except Exception as e:
            raise StreamError(e)

    def close(self):
        """
        Closes the stream subscription by aborting its underlying http request.
        """
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

            stream_url = self._client.base_url + "/stream%s" % (url_params)
            with self.conn.stream(
                    "POST",
                    stream_url,
                    content=self._data,
                    headers=dict(headers),
            ) as stream_response:
                self._state = "open"
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
            for push in stream_response.iter_bytes():
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
                        self._client.sync_last_txn_time(cast(Any, event).txn)
                    on_event(event, request_result)
                    if self._client.observer is not None:
                        self._client.observer(request_result)
                if self._state == "closed":
                    break
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
