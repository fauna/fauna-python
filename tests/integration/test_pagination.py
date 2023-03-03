from fauna import fql


def test_client_handles_pagination(client, a_collection):
    q = fql('$col.create({ "foo": "bar" })', col=a_collection)

    for _ in range(0, 100):
        client.query(q)

    q = fql('$col.all', col=a_collection)

    data = client.query(q).data
    total = len(data['data'])

    while 'after' in data:
        p = fql('Set.paginate($token)', token=data['after'])
        data = client.query(p).data
        total += len(data['data'])

    assert total == 100


def test_response_iterator(client, a_collection):
    q = fql('$col.create({ "foo": "bar" })', col=a_collection)

    for _ in range(0, 100):
        client.query(q)

    q = fql('$col.all', col=a_collection)
    total = 0

    for page in client.query(q).pages():
        total += len(page.data['data'])

    assert total == 100

