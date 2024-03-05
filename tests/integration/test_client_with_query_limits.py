from multiprocessing.pool import ThreadPool
import os

import pytest

from fauna import fql
from fauna.client import Client
from fauna.encoding import QuerySuccess
from fauna.errors.errors import ThrottlingError


def query_collection(client: Client) -> QuerySuccess | None:
  coll_name = os.environ.get("QUERY_LIMITS_COLL") or ""
  try:
    return client.query(fql("${coll}.all().paginate(50)", coll=fql(coll_name)))
  # Ignore ThrottlingErrors - just means retries were exhausted
  except ThrottlingError:
    return None


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

    # Expect at least one client to have succeeded on retry
    for result in results:
      if result is not None and result.stats.attempts > 1:
        throttled = True

  assert throttled == True

  for cl in clients:
    cl.close()
