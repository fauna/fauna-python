import time
import pytest

from fauna import fql
from fauna.client import ChangeFeedOptions
from fauna.errors import AbortError


def test_change_feed_requires_stream(client, a_collection):
  with pytest.raises(
      TypeError,
      match="'fql' must be a EventSource, or a Query that returns a EventSource but was a <class 'int'>."
  ):
    client.change_feed(fql("42"))


def test_change_feed_query(client, a_collection):
  feed = client.change_feed(fql("${col}.all().toStream()", col=a_collection))
  _pull_one_event(client, a_collection, feed)


def test_change_feed_event_source(client, a_collection):
  source = client.query(fql("${col}.all().toStream()", col=a_collection)).data
  feed = client.change_feed(source)
  _pull_one_event(client, a_collection, feed)


def _pull_one_event(client, col, feed):
  client.query(fql("${col}.create({ foo: 'bar' })", col=col))

  pages = list(feed)
  assert len(pages) == 1
  assert len(pages[0]) == 1

  events = list(pages[0])
  assert events[0]['type'] == 'add'
  assert events[0]['data']['foo'] == 'bar'


def test_change_feeds_error_event(client, a_collection):
  feed = client.change_feed(
      fql("${col}.all().map(_ => abort('oops')).toStream()", col=a_collection))

  client.query(fql("${col}.create({ foo: 'bar' })", col=a_collection))

  with pytest.raises(AbortError):
    list(feed.flatten())


@pytest.mark.xfail(reason="pending core support")
def test_change_feeds_continue_after_an_error(client, a_collection):
  feed = client.change_feed(
      fql('''
      ${col}
        .all()
        .map(doc =>
          if (doc.n == 1) abort('oops')
          else doc
        )
        .toStream()
      ''',
          col=a_collection))

  client.query(
      fql('''
      Set
        .sequence(0, 3)
        .forEach(n => ${col}.create({ n: n }))
      ''',
          col=a_collection))

  events = []

  for page in feed:
    try:
      for event in page:
        events.append(event['data']['n'])
    except AbortError:
      pass

  assert events == [0, 2]


def test_change_feed_start_ts(client, a_collection):
  source = client.query(
      fql("${col}.all().map(.n).toStream()", col=a_collection)).data

  # NB. Issue separate queries to ensure they get different txn times.
  _create_docs(client, a_collection, 0, 1)
  _create_docs(client, a_collection, 1, 64)

  # NB. Use a short page size to ensure that more than one roundtrip is made,
  # thus testing the interator's internal cursoring is correct.
  first = next(client.change_feed(source).flatten())
  opts = ChangeFeedOptions(start_ts=first['txn_ts'], page_size=5)
  feed = client.change_feed(source, opts)

  nums = [event['data'] for event in feed.flatten()]
  assert nums == list(range(1, 64))


def test_change_feed_cursor(client, a_collection):
  source = client.query(
      fql("${col}.all().map(.n).toStream()", col=a_collection)).data

  _create_docs(client, a_collection, 0, 64)

  # NB. Use a short page size to ensure that more than one roundtrip is made,
  # thus testing the interator's internal cursoring is correct.
  first = next(client.change_feed(source).flatten())
  opts = ChangeFeedOptions(cursor=first['cursor'], page_size=5)
  feed = client.change_feed(source, opts)

  nums = [event['data'] for event in feed.flatten()]
  assert nums == list(range(1, 64))


def test_rejects_when_both_start_ts_and_cursor_provided(scoped_client):
  scoped_client.query(fql("Collection.create({name: 'Product'})"))

  response = scoped_client.query(fql("Product.all().toStream()"))
  source = response.data

  with pytest.raises(TypeError):
    opts = ChangeFeedOptions(cursor="abc1234==", start_ts=response.txn_ts)
    scoped_client.change_feed(source, opts)


def test_change_feed_reusable_iterator(client, a_collection):
  feed = client.change_feed(
      fql("${col}.all().map(.n).toStream()", col=a_collection))

  _create_docs(client, a_collection, 0, 5)
  nums = [event['data'] for event in feed.flatten()]
  assert nums == list(range(0, 5))

  _create_docs(client, a_collection, 5, 10)
  nums = [event['data'] for event in feed.flatten()]
  assert nums == list(range(5, 10))


def _create_docs(client, col, start=0, end=1):
  client.query(
      fql(
          '''
      Set
        .sequence(${start}, ${end})
        .forEach(n => ${col}.create({ n: n }))
      ''',
          start=start,
          end=end,
          col=col,
      ))
