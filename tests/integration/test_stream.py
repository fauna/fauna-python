import threading
from datetime import timedelta

import pytest

from fauna import fql
from fauna.client import StreamOptions


def test_stream(client, a_collection):

  opts = StreamOptions(
      idle_timeout=timedelta(seconds=1), retry_on_timeout=False)

  def thread_fn():
    stream = client.stream(
        fql("${coll}.all().toStream()", coll=a_collection), opts)

    with stream as iter:
      events = [evt["type"] for evt in iter]

    assert events == ["start", "add", "remove", "add"]

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()

  id = client.query(fql("${coll}.create({}).id", coll=a_collection)).data
  client.query(fql("${coll}.byId(${id})!.delete()", coll=a_collection, id=id))
  client.query(fql("${coll}.create({}).id", coll=a_collection))

  stream_thread.join()


def test_retry_on_timeout(client, a_collection):

  opts = StreamOptions(
      idle_timeout=timedelta(seconds=0.1), retry_on_timeout=True)

  def thread_fn():
    stream = client.stream(
        fql("${coll}.all().toStream()", coll=a_collection), opts)

    events = []
    with stream as iter:
      for evt in iter:
        events.append(evt["type"])
        if len(events) == 4:
          iter.close()

    assert events == ["start", "start", "start", "start"]

  stream_thread = threading.Thread(target=thread_fn)
  stream_thread.start()
  stream_thread.join()
