import threading

import httpx
import pytest

from fauna import fql
from fauna.client import Client, StreamOptions
from fauna.errors import ClientError, RetryableFaunaException, QueryRuntimeError, NetworkError
from fauna.http.httpx_client import HTTPXClient


def test_stream(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  barrier = threading.Barrier(2)
  events = []

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))
    barrier.wait()

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 3 events
        if len(events) == 3:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()
  barrier.wait()

  id = scoped_client.query(fql("Product.create({}).id")).data
  scoped_client.query(fql("Product.byId(${id})!.delete()", id=id))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["add", "remove", "add"]


def test_close_method(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  barrier = threading.Barrier(2)
  events = []

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))
    barrier.wait()

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 2 events
        if len(events) == 2:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()
  barrier.wait()

  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["add", "add"]


def test_error_on_stream(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  barrier = threading.Barrier(2)

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().map(.foo / 0).toStream()"))
    barrier.wait()

    with pytest.raises(QueryRuntimeError):
      with stream as iter:
        for evt in iter:
          pass

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()
  barrier.wait()

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

  old_send = httpx_client.send

  def send_func(*args, **kwargs):
    if not kwargs['stream']:
      return old_send(*args, **kwargs)

    count[0] += 1
    raise NetworkError('foo')

  httpx_client.send = send_func

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

  barrier = threading.Barrier(2)
  events = []

  def thread_fn():
    stream = scoped_client.stream(fql("Product.all().toStream()"))
    barrier.wait()

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
  barrier.wait()

  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["add", "add", "add"]


def test_providing_start_ts(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  source = scoped_client.query(fql("Product.all().toStream()")).data

  createOne = scoped_client.query(fql("Product.create({})"))
  createTwo = scoped_client.query(fql("Product.create({})"))
  createThree = scoped_client.query(fql("Product.create({})"))

  barrier = threading.Barrier(2)
  events = []

  def thread_fn():
    # replay excludes the ts that was passed in, it provides events for all ts after the one provided
    stream = scoped_client.stream(source,
                                  StreamOptions(start_ts=createOne.txn_ts))
    barrier.wait()
    with stream as iter:
      for event in iter:
        events.append(event)
        if (len(events) == 3):
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()
  barrier.wait()

  createFour = scoped_client.query(fql("Product.create({})"))
  stream_thread.join()
  assert events[0]["txn_ts"] == createTwo.txn_ts
  assert events[1]["txn_ts"] == createThree.txn_ts
  assert events[2]["txn_ts"] == createFour.txn_ts


def test_providing_cursor(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  source = scoped_client.query(fql("Product.all().toStream()")).data
  create1 = scoped_client.query(fql("Product.create({ value: 1 })"))
  create2 = scoped_client.query(fql("Product.create({ value: 2 })"))

  cursor = None
  with scoped_client.stream(source) as iter:
    for event in iter:
      assert event["type"] == "add"
      assert event["data"]["value"] == 1
      cursor = event["cursor"]
      break

  opts = StreamOptions(cursor=cursor)
  with scoped_client.stream(source, opts) as iter:
    for event in iter:
      assert event["type"] == "add"
      assert event["data"]["value"] == 2
      break


def test_rejects_cursor_with_fql_query(scoped_client):
  with pytest.raises(
      ClientError,
      match="The 'cursor' configuration can only be used with an event source."
  ):
    opts = StreamOptions(cursor="abc1234==")
    scoped_client.stream(fql("Collection.create({name: 'Product'})"), opts)


def test_rejects_when_both_start_ts_and_cursor_provided(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  response = scoped_client.query(fql("Product.all().toStream()"))
  source = response.data

  with pytest.raises(TypeError):
    opts = StreamOptions(cursor="abc1234==", start_ts=response.txn_ts)
    scoped_client.stream(source, opts)


def test_handle_status_events(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  barrier = threading.Barrier(2)
  events = []

  def thread_fn():
    opts = StreamOptions(status_events=True)
    stream = scoped_client.stream(fql("Product.all().toStream()"), opts)
    barrier.wait()

    with stream as iter:
      for evt in iter:
        events.append(evt["type"])

        # close after 3 events
        if len(events) == 3:
          iter.close()

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()
  barrier.wait()

  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))
  scoped_client.query(fql("Product.create({})"))

  stream_thread.join()
  assert events == ["status", "add", "add"]
