import sys
import os
import platform
from faunadb.client import FaunaClient
from faunadb.errors import UnexpectedError
from tests.helpers import FaunaTestCase
from faunadb import __version__ as pkg_version, __api_version__ as api_version

class ClientTest(FaunaTestCase):

  def test_ping(self):
    old_time = self.client.get_last_txn_time()
    self.assertEqual(self.client.ping("node"), "Scope node is OK")
    new_time = self.client.get_last_txn_time()

    self.assertEqual(old_time, new_time) # client.ping should not update last-txn-time

  def test_query_timeout(self):
    client = FaunaClient(secret="secret", query_timeout_ms=5000)
    self.assertEqual(client.get_query_timeout(), 5000)

  def test_last_txn_time(self):
    old_time = self.client.get_last_txn_time()
    self.client.query({})
    new_time = self.client.get_last_txn_time()

    self.assertTrue(old_time < new_time) # client.query should update last-txn-time

  def test_last_txn_time_upated(self):
    first_seen = self.client.get_last_txn_time()

    new_time = first_seen - 12000
    self.client.sync_last_txn_time(new_time)
    self.assertEqual(self.client.get_last_txn_time(), first_seen) # last-txn can not be smaller

    new_time = first_seen + 12000
    self.client.sync_last_txn_time(new_time)
    self.assertEqual(self.client.get_last_txn_time(), new_time) # last-txn can move forward

  def test_error_on_closed_client(self):
    client = FaunaClient(secret="secret")
    client.__del__()
    self.assertRaisesRegexCompat(UnexpectedError,
                                 "Cannnot create a session client from a closed session",
                                 lambda: client.new_session_client(secret="new_secret"))

  def test_runtime_env_headers(self):
    client = FaunaClient(secret="secret")
    headers = client.session.headers
    self.assertEqual(headers["X-Fauna-Driver-Version"], pkg_version)
    self.assertEqual(headers["X-FaunaDB-API-Version"], api_version)
    self.assertEqual(headers["X-Python-Version"], "{0}.{1}.{2}-{3}".format(*sys.version_info))
    self.assertEqual(headers["X-Runtime-Environment-OS"], platform.system().lower())
    self.assertEqual(headers["X-Runtime-Environment"], "Unknown")

  def test_recognized_runtime_env_headers(self):
    originalPath = os.environ["PATH"]
    os.environ["PATH"] = originalPath + ".heroku"

    client = FaunaClient(secret="secret")
    self.assertEqual(client.session.headers["X-Runtime-Environment"], "Heroku")

    os.environ["PATH"] = originalPath


