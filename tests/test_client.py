from typing import cast
import sys
import os
import platform
from faunadb.client import FaunaClient, FaunaClientConfiguration
from faunadb.errors import UnexpectedError
from tests.conftest import FaunaTestCase
from faunadb import __version__ as pkg_version, __api_version__ as api_version


class ClientTest(FaunaTestCase):

    def test_endpoint_normalization(self):
        endpoint = self._get_fauna_endpoint()
        endpoints = [
            endpoint, endpoint + "/", endpoint + "//", endpoint + "\\",
            endpoint + "\\\\"
        ]
        for e in endpoints:
            client = FaunaClient(
                FaunaClientConfiguration(secret="secret", endpoint=e))
            client.configuration.endpoint
            self.assertEqual(client.configuration.endpoint, endpoint)

    def test_query_timeout(self):
        client = FaunaClient(configuration=FaunaClientConfiguration(
            secret="secret", timeout_ms=5000))

        self.assertEqual(client.get_query_timeout(), 5000)

    def test_last_txn_time(self):
        self.client.query("Time.now()")
        old_time = cast(int, self.client.get_last_txn_time())
        self.client.query("Time.now()")
        new_time = cast(int, self.client.get_last_txn_time())
        self.assertTrue(
            old_time < new_time)  # client.query should update last-txn-time

    def test_last_txn_time_upated(self):
        self.client.query("Time.now()")
        first_seen = cast(int, self.client.get_last_txn_time())

        new_time = first_seen - 12000
        self.client.sync_last_txn_time(new_time)
        self.assertEqual(self.client.get_last_txn_time(),
                         first_seen)  # last-txn can not be smaller

        new_time = first_seen + 12000
        self.client.sync_last_txn_time(new_time)
        self.assertEqual(self.client.get_last_txn_time(),
                         new_time)  # last-txn can move forward

    def test_runtime_env_headers(self):
        client = FaunaClient(FaunaClientConfiguration(secret="secret"))

        self.assertEqual(
            client._headers['X-Driver-Env'],
            "driver=python-{0}; runtime=python-{1} env={2}; os={3}".format(
                pkg_version, "{0}.{1}.{2}-{3}".format(*sys.version_info),
                "Unknown", "{0}-{1}".format(platform.system(),
                                            platform.release())).lower())

    def test_recognized_runtime_env_headers(self):
        originalPath = os.environ["PATH"]
        os.environ["PATH"] = originalPath + ".heroku"

        client = FaunaClient(FaunaClientConfiguration(secret="secret"))

        self.assertEqual(
            client._headers['X-Driver-Env'],
            "driver=python-{0}; runtime=python-{1} env={2}; os={3}".format(
                pkg_version, "{0}.{1}.{2}-{3}".format(*sys.version_info),
                "Heroku", "{0}-{1}".format(platform.system(),
                                           platform.release())).lower())

        os.environ["PATH"] = originalPath
