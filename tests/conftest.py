from typing import cast
import string
import random
import warnings
from collections import namedtuple
from logging import getLogger, WARNING
from os import environ
from unittest import TestCase
import pytest

import httpx

from faunadb._json import to_json, parse_json
from faunadb.client import FaunaClient, FaunaClientConfiguration

_FAUNA_ROOT_KEY = environ["FAUNA_ROOT_KEY"]
_FAUNA_ENDPOINT = environ["FAUNA_ENDPOINT"]


@pytest.fixture(scope="module") 
def root_client():
    return FaunaClient(configuration=FaunaClientConfiguration(
        secret=_FAUNA_ROOT_KEY,
        endpoint=_FAUNA_ENDPOINT,
    ))


class FaunaTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(FaunaTestCase, cls).setUpClass()

        cls.root_client = cls._get_client()

        rnd = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        cls.db_name = "faunadb-python-test" + rnd
        # cls.db_ref = query.database(cls.db_name)

        cls.client = cls.root_client.new_session_client()

        # db_exists = cls.root_client.query(query.exists(cls.db_ref))
        # if db_exists:
        #     cls.root_client.query(query.delete(cls.db_ref))

        # cls.root_client.query(query.create_database({"name": cls.db_name}))

        # cls.server_key = cls.root_client.query(
        #     query.create_key({
        #         "database": cls.db_ref,
        #         "role": "server"
        #     }))["secret"]
        # cls.client = cls.root_client.new_session_client(secret=cls.server_key)

        # cls.admin_key = cls.root_client.query(
        #     query.create_key({
        #         "database": cls.db_ref,
        #         "role": "admin"
        #     }))["secret"]
        # cls.admin_client = cls.root_client.new_session_client(
        #     secret=cls.admin_key)

    @classmethod
    def tearDownClass(cls):
        pass
        # cls.root_client.query(query.delete(cls.db_ref))

    def assertJson(self, obj, json):
        self.assertToJson(obj, json)
        self.assertParseJson(obj, json)

    def assertToJson(self, obj, json):
        self.assertEqual(to_json(obj, sort_keys=True), json)

    def assertParseJson(self, obj, json):
        self.assertEqual(parse_json(json), obj)

    def assertRegexCompat(self, text, regex, msg=None):
        # pylint: disable=deprecated-method
        with warnings.catch_warnings():
            # Deprecated in 3.x but 2.x does not have it under the new name.
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self.assertRegexpMatches(text, regex, msg=msg)

    def assertRaisesRegexCompat(self, exception, regexp, callable, *args,
                                **kwds):
        # pylint: disable=deprecated-method
        with warnings.catch_warnings():
            # Deprecated in 3.x but 2.x does not have it under the new name.
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self.assertRaisesRegexp(exception, regexp, callable, *args, **kwds)

    @classmethod
    def _get_client(cls):
        return FaunaClient(configuration=FaunaClientConfiguration(
            secret=_FAUNA_ROOT_KEY,
            endpoint=_FAUNA_ENDPOINT,
        ))

    @classmethod
    def _get_fauna_endpoint(cls):
        return _FAUNA_ENDPOINT

    def assert_raises(self, exception_class, action):
        """Like self.assertRaises and returns the exception too."""
        with self.assertRaises(exception_class) as cm:
            action()
        return cm.exception


def mock_client(response_text, status_code=httpx.codes.OK):
    c = FaunaClient()
    c.session = cast(httpx.Client, _MockSession(response_text, status_code))
    return cast(FaunaClient, c)


class _MockSession(object):

    def __init__(self, response_text, status_code):
        self.response_text = response_text
        self.status_code = status_code

    def close(self):
        pass

    def build_request(self, *args, **kwords):
        return _MockResponse(self.status_code, self.response_text, {})

    def send(self, req, *args):
        # pylint: disable=unused-argument
        return req


_MockResponse = namedtuple('MockResponse', ['status_code', 'text', 'headers'])
