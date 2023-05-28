from fauna import fql


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
