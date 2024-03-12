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


def test_stream(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))
  scoped_client.query(fql("Product.create({})"))

  events = [[]]

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))

    with stream as iter:
      events[0] = [evt["type"] for evt in take(iter, 3)]

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  id = scoped_client.query(fql("Product.create({}).id")).data
  scoped_client.query(fql("Product.byId(${id})!.delete()", id=id))
  scoped_client.query(fql("Product.create({}).id"))

  stream_thread.join()
  assert events[0] == ["add", "remove", "add"]


def test_close_method(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  events = []

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 2 events
        if len(events) == 2:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  scoped_client.query(fql("Product.create({}).id")).data
  scoped_client.query(fql("Product.create({}).id")).data

  stream_thread.join()
  assert events == ["add", "add"]


def test_max_retries(scoped_secret):
  scoped_client = Client(secret=scoped_secret)
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  httpx_client = httpx.Client(http1=False, http2=True)
  client = Client(
      secret=scoped_secret,
      http_client=HTTPXClient(httpx_client),
      max_attempts=3,
      max_backoff=0)

  count = [0]

  def stream_func(*args, **kwargs):
    count[0] += 1
    raise NetworkError('foo')

  httpx_client.stream = stream_func

  count[0] = 0
  with pytest.raises(RetryableFaunaException):
    with client.stream(fql("Product.all().toStream()")) as iter:
      events = [evt["type"] for evt in iter]
  assert count[0] == 3

  count[0] = 0
  with pytest.raises(RetryableFaunaException):
    opts = StreamOptions(max_attempts=5)
    with client.stream(fql("Product.all().toStream()"), opts) as iter:
      events = [evt["type"] for evt in iter]
  assert count[0] == 5
