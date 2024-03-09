import threading
from datetime import timedelta

import pytest
import httpx
import fauna

from fauna import fql
from fauna.client import Client, StreamOptions
from fauna.http.httpx_client import HTTPXClient
from fauna.errors import NetworkError, RetryableFaunaException


def take(stream, count):
  i = iter(stream)

  while count > 0:
    count -= 1
    yield next(i)


def test_stream(client, a_collection):

  events = [[]]

  def thread_fn():
    stream = client.stream(fql("${coll}.all().toStream()", coll=a_collection))

    with stream as iter:
      events[0] = [evt["type"] for evt in take(iter, 3)]

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  id = client.query(fql("${coll}.create({}).id", coll=a_collection)).data
  client.query(fql("${coll}.byId(${id})!.delete()", coll=a_collection, id=id))
  client.query(fql("${coll}.create({}).id", coll=a_collection))

  stream_thread.join()
  assert events[0] == ["add", "remove", "add"]


def test_close_method(client, a_collection):

  events = []

  def thread_fn():
    stream = client.stream(fql("${coll}.all().toStream()", coll=a_collection))

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 2 events
        if len(events) == 2:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  client.query(fql("${coll}.create({}).id", coll=a_collection)).data
  client.query(fql("${coll}.create({}).id", coll=a_collection)).data

  stream_thread.join()
  assert events == ["add", "add"]


def test_max_retries(a_collection):
  httpx_client = httpx.Client(http1=False, http2=True)
  client = Client(
      http_client=HTTPXClient(httpx_client), max_attempts=3, max_backoff=1)

  count = [0]

  def stream_func(*args, **kwargs):
    count[0] += 1
    raise NetworkError('foo')

  httpx_client.stream = stream_func

  count[0] = 0
  with pytest.raises(RetryableFaunaException):
    with client.stream(fql("${coll}.all().toStream()",
                           coll=a_collection)) as iter:
      events = [evt["type"] for evt in iter]
  assert count[0] == 3

  count[0] = 0
  with pytest.raises(RetryableFaunaException):
    opts = StreamOptions(max_attempts=5)
    with client.stream(
        fql("${coll}.all().toStream()", coll=a_collection), opts) as iter:
      events = [evt["type"] for evt in iter]
  assert count[0] == 5
