from datetime import timedelta

import pytest

from fauna import fql
from fauna.client.client import QueryOptions
from fauna.errors.errors import QueryTimeoutError


def test_single_page_with_small_collection(client, pagination_collections):
    small_coll, _ = pagination_collections

    query_iterator = client.paginate(fql("${mod}.all()", mod=small_coll))

    page_count = 0
    for page in query_iterator:
        page_count += 1
        assert len(page) == 10

    assert page_count == 1


def test_multiple_pages_with_big_collection(client, pagination_collections):
    _, big_coll = pagination_collections

    query_iterator = client.paginate(fql("${mod}.all()", mod=big_coll))

    page_count = 0
    for _ in query_iterator:
        page_count += 1

    assert page_count == 2


def test_iterator_can_be_flattened(client, pagination_collections):
    _, big_coll = pagination_collections

    query_iterator = client.paginate(fql("${mod}.all()", mod=big_coll))

    page_count = 0
    for _ in query_iterator.flatten():
        page_count += 1

    assert page_count == 20


def test_iterator_can_paginate_non_page(client):
    query_iterator = client.paginate(fql("[0,1,2,3,4]"))

    page_count = 0
    for page in query_iterator:
        # If the query response is not a page, then the whole thing gets
        # stuffed into the result. That is, array responses are not treated like
        # pages.
        assert page == [[0, 1, 2, 3, 4]]
        page_count += 1

    assert page_count == 1


def test_iterator_can_flatten_non_page(client):
    query_iterator = client.paginate(fql("[0,1,2,3,4]"))

    page_count = 0
    for item in query_iterator.flatten():
        assert item == [0, 1, 2, 3, 4]
        page_count += 1

    assert page_count == 1


def test_can_get_pages_using_next(client, pagination_collections):
    _, big_coll = pagination_collections

    query_iterator = client.paginate(fql("${mod}.all()", mod=big_coll))

    my_iter = query_iterator.iter()

    first = next(my_iter)
    assert len(first) == 16

    second = next(my_iter)
    assert len(second) == 4


def test_can_get_pages_using_a_loop_with_next(client, pagination_collections):
    _, big_coll = pagination_collections

    query_iterator = client.paginate(fql("${mod}.all()", mod=big_coll))

    my_iter = query_iterator.iter()

    page_count = 0
    try:
        while True:
            _ = next(my_iter)
            page_count += 1
    except StopIteration:
        pass  # Iterator exhausted, exit the loop

    assert page_count == 2


@pytest.mark.skip(reason="query_timeout not properly handled yet")
def test_respects_query_options(client, pagination_collections):
    _, big_coll = pagination_collections

    query_iterator = client.paginate(
        fql("${mod}.create({ name: 'Wah' })", mod=big_coll),
        QueryOptions(query_timeout=timedelta(milliseconds=1)))

    try:
        next(query_iterator.iter())
    except QueryTimeoutError:
        assert True

    assert False
