from fauna.encoding import QuerySuccess, QueryInfo, QueryStats


def test_query_success_repr():
  qs = QuerySuccess(
      data={'foo': 'bar'},
      query_tags={'tag': 'value'},
      static_type=None,
      stats=QueryStats({'compute_ops': 1}),
      summary="human readable",
      traceparent=None,
      txn_ts=123,
      schema_version=123,
  )
  stats = "{'compute_ops': 1, 'read_ops': 0, 'write_ops': 0, " \
          "'query_time_ms': 0, 'storage_bytes_read': 0, 'storage_bytes_write': 0, " \
          "'contention_retries': 0}"
  assert repr(qs) == "QuerySuccess(query_tags={'tag': 'value'}," \
                     "static_type=None," \
                     f"stats=QueryStats(stats={stats})," \
                     "summary='human readable'," \
                     "traceparent=None," \
                     "txn_ts=123," \
                     "schema_version=123," \
                     "data={'foo': 'bar'})"

  evaluated: QuerySuccess = eval(repr(qs))
  assert evaluated.txn_ts == qs.txn_ts
  assert evaluated.schema_version == qs.schema_version
  assert evaluated.traceparent == qs.traceparent
  assert evaluated.query_tags == qs.query_tags
  assert evaluated.data == qs.data
  assert evaluated.static_type == qs.static_type
  assert evaluated.summary == qs.summary
  assert evaluated.stats == qs.stats


def test_query_info_repr():
  qi = QueryInfo(
      query_tags={'tag': 'value'},
      stats=QueryStats({'compute_ops': 1}),
      summary="human readable",
      txn_ts=123,
      schema_version=123,
  )
  stats = "{'compute_ops': 1, 'read_ops': 0, 'write_ops': 0, " \
          "'query_time_ms': 0, 'storage_bytes_read': 0, 'storage_bytes_write': 0, " \
          "'contention_retries': 0}"
  assert repr(qi) == "QueryInfo(query_tags={'tag': 'value'}," \
                     f"stats=QueryStats(stats={stats})," \
                     "summary='human readable'," \
                     "txn_ts=123," \
                     "schema_version=123)"

  evaluated: QueryInfo = eval(repr(qi))
  assert evaluated.txn_ts == qi.txn_ts
  assert evaluated.query_tags == qi.query_tags
  assert evaluated.summary == qi.summary
  assert evaluated.stats == qi.stats
  assert evaluated.schema_version == qi.schema_version


def test_query_stats_repr():
  qs = QueryStats({
      'compute_ops': 1,
      'read_ops': 2,
      'write_ops': 3,
      'query_time_ms': 4,
      'storage_bytes_read': 5,
      'storage_bytes_write': 6,
      'contention_retries': 7
  })

  stats = "{'compute_ops': 1, 'read_ops': 2, 'write_ops': 3, " \
          "'query_time_ms': 4, 'storage_bytes_read': 5, 'storage_bytes_write': 6, " \
          "'contention_retries': 7}"

  assert repr(qs) == f"QueryStats(stats={stats})"

  evaluated: QueryStats = eval(repr(qs))

  assert evaluated == qs
