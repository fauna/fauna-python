from fauna.client import QuerySuccess, QueryInfo


def test_query_success_repr():
    qs = QuerySuccess(
        data={'foo': 'bar'},
        query_tags={'tag': 'value'},
        static_type=None,
        stats={'stat': 1},
        summary="human readable",
        traceparent=None,
        txn_ts=123,
    )

    assert repr(qs) == "QuerySuccess(query_tags={'tag': 'value'}," \
                       "static_type=None," \
                       "stats={'stat': 1}," \
                       "summary='human readable'," \
                       "traceparent=None," \
                       "txn_ts=123," \
                       "data={'foo': 'bar'})"

    evaluated: QuerySuccess = eval(repr(qs))
    assert evaluated.txn_ts == qs.txn_ts
    assert evaluated.traceparent == qs.traceparent
    assert evaluated.query_tags == qs.query_tags
    assert evaluated.data == qs.data
    assert evaluated.static_type == qs.static_type
    assert evaluated.summary == qs.summary
    assert evaluated.stats == qs.stats


def test_query_info_repr():
    qi = QueryInfo(
        query_tags={'tag': 'value'},
        stats={'stat': 1},
        summary="human readable",
        txn_ts=123,
    )

    assert repr(qi) == "QueryInfo(query_tags={'tag': 'value'}," \
                       "stats={'stat': 1}," \
                       "summary='human readable'," \
                       "txn_ts=123)"

    evaluated: QueryInfo = eval(repr(qi))
    assert evaluated.txn_ts == qi.txn_ts
    assert evaluated.query_tags == qi.query_tags
    assert evaluated.summary == qi.summary
    assert evaluated.stats == qi.stats
