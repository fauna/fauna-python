from fauna import fql, Document


def test_subquery_composition(client, a_collection):
  test_email = "foo@fauna.com"
  index = {
      "indexes": {
          "byEmail": {
              "terms": [{
                  "field": "email"
              }],
              "values": [{
                  "field": "email"
              }]
          }
      }
  }

  client.query(
      fql("${col}.definition.update(${idx})", col=a_collection, idx=index))
  doc = client.query(
      fql("${col}.create(${doc})",
          col=a_collection,
          doc={
              "email": test_email,
              "alias": "bar"
          })).data

  def doc_by_email(email: str):
    return fql(
        "${col}.byEmail(${email}).first()", col=a_collection, email=email)

  def update_doc_by_email(email: str, data: dict):
    q = """
let u = ${user}
u.update(${data})
"""
    return fql(q, user=doc_by_email(email), data=data)

  result = client.query(update_doc_by_email(test_email, {"alias": "baz"}))

  assert isinstance(result.data, Document)
  assert result.data["email"] == test_email
  assert result.data["alias"] == "baz"
  assert result.data.id == doc.id
  assert result.data.coll == doc.coll
  assert result.data.ts != doc.ts


def test_array_composition(client):
  queries = [
      fql("1"),
      fql("2"), {
          "key": 3
      }, [fql("${inner}", inner={"inner": "thing"})]
  ]
  q = fql("${queries}", queries=queries)
  res = client.query(q).data
  assert [1, 2, {'key': 3}, [{'inner': 'thing'}]] == res


def test_object_composition(client):
  queries = {
      1: fql("1"),
      2: fql("2"),
      3: {
          "key": fql("3")
      },
      4: {
          "inner": fql("${inner}", inner=["inner", "thing"])
      }
  }
  q = fql("${queries}", queries=queries)
  res = client.query(q).data
  assert {
      '1': 1,
      '2': 2,
      '3': {
          'key': 3
      },
      '4': {
          'inner': ['inner', 'thing']
      }
  } == res
