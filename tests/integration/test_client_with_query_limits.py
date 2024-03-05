from multiprocessing.pool import ThreadPool
import os

import pytest

from fauna import fql
from fauna.client import Client
from fauna.encoding import QuerySuccess


def query_collection(client: Client) -> QuerySuccess:
  coll_name = os.environ.get("QUERY_LIMITS_COLL") or ""
  page_size = os.environ.get("QUERY_LIMITS_PAGE_SIZE") or "10"
  return client.query(fql("${coll}.all().paginate(${page})", coll=fql(coll_name), page=int(page_size)))


@pytest.mark.skipif(
    "QUERY_LIMITS_DB" not in os.environ or
    "QUERY_LIMITS_COLL" not in os.environ,
    reason="QUERY_LIMITS_DB and QUERY_LIMITS_COLL must both be set to run this test"
)
def test_client_retries_throttled_query():
  db_name = os.environ.get("QUERY_LIMITS_DB")
  rootClient = Client()
  res = rootClient.query(
      fql("""
if (Database.byName(${db}).exists()) {
  Key.create({ role: "admin", database: ${db} }) { secret }
} else {
  abort("Database not found.")
}""",
          db=db_name))
  secret = res.data["secret"]
  clients = [Client(secret=secret) for _ in range(5)]
  throttled = False

  with ThreadPool() as pool:
    results = pool.map(query_collection, clients)

    for result in results:
      if result.stats.attempts > 1:
        throttled = True

  assert throttled == True

  for cl in clients:
    cl.close()
