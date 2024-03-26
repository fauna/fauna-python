import threading
import time
import pytest
import httpx
import fauna
from fauna import fql
from fauna.client import Client, StreamOptions
from fauna.http.httpx_client import HTTPXClient
from fauna.errors import NetworkError, RetryableFaunaException, QueryRuntimeError


def test_stream(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  events = []

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 3 events
        if len(events) == 3:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  # adds a delay so the thread can open the stream,
  # otherwise we could miss some events
  time.sleep(0.5)

  id = scoped_client.query(fql("Product.create({}).id")).data
  scoped_client.query(fql("Product.byId(${id})!.delete()", id=id))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["add", "remove", "add"]


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

  # adds a delay so the thread can open the stream,
  # otherwise we could miss some events
  time.sleep(0.5)

  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["add", "add"]


def test_error_on_stream(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().map(.foo / 0).toStream()"))

    with pytest.raises(QueryRuntimeError):
      with stream as iter:
        for evt in iter:
          pass

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  # adds a delay so the thread can open the stream,
  # otherwise we could miss some events
  time.sleep(0.5)

  scoped_client.query(fql("Product.create({foo: 10})"))
  scoped_client.query(fql("Product.create({foo: 10})"))

  stream_thread.join()


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


def test_last_ts_is_monotonic(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  events = []

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))

    with stream as iter:
      last_ts = 0

      for evt in iter:
        assert iter.last_ts > last_ts

        last_ts = iter.last_ts

        events.append(evt["type"])

        # close after 3 events
        if len(events) == 3:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  # adds a delay so the thread can open the stream,
  # otherwise we could miss some events
  time.sleep(0.5)

  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["add", "add", "add"]

def test_providing_start_ts(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  stream_token = scoped_client.query(fql("Product.all().toStream()")).data

  createOne = scoped_client.query(fql("Product.create({})"))
  createTwo = scoped_client.query(fql("Product.create({})"))
  createThree = scoped_client.query(fql("Product.create({})"))

  events = []
  def thread_fn():
    # replay excludes the ts that was passed in, it provides events for all ts after the one provided
    stream = scoped_client.stream(stream_token, StreamOptions(start_ts=createOne.txn_ts))
    with stream as iter:
      for event in iter:
        events.append(event)
        if (len(events) == 3):
          iter.close()
  
  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  # adds a delay so the thread can open the stream,
  # otherwise we could miss some events
  time.sleep(0.5)

  createFour = scoped_client.query(fql("Product.create({})"))
  stream_thread.join()
  assert events[0]["txn_ts"] == createTwo.txn_ts
  assert events[1]["txn_ts"] == createThree.txn_ts
  assert events[2]["txn_ts"] == createFour.txn_ts

@pytest.mark.xfail(reason="not currently supported by core")
def test_handle_status_events(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  events = []

  def thread_fn():
    opts = StreamOptions(status_events=True)
    stream = scoped_client.stream(fql("Product.all().toStream()"), opts)

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 3 events
        if len(events) == 3:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  # adds a delay so the thread can open the stream,
  # otherwise we could miss some events
  time.sleep(0.5)

  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["status", "add", "add"]
