from datetime import datetime
from unittest import TestCase
import iso8601

from faunadb._json import to_json


class SerializationTest(TestCase):

    def test_fauna_time(self):
        self.assertJson(datetime.fromtimestamp(0, iso8601.UTC),
                        '{"@time":"1970-01-01T00:00:00Z"}')
        self.assertJson(
            datetime.fromtimestamp(0, iso8601.UTC).date(),
            '{"@date":"1970-01-01T00:00:00Z"}')

    def test_primitives(self):
        self.assertJson(1, {"@int": "1"})
        self.assertJson(2**62, {"@long": "1"})
        self.assertJson(2.0, {"@float": "2.0"})
        self.assertJson("2.0", "2.0")

    def test_objects(self):
        self.assertJson({"a": 2}, {"a": {"@int": 2}})
        self.assertJson(
            {
                "@a": 2,
                "bob": 2.0
            },
            {"@object": {
                "@a": {
                    "@int": 2
                },
                "bob": {
                    "@float": 2.0
                }
            }},
        )

    def assertJson(self, obj, expected):
        self.assertEqual(to_json(obj, sort_keys=True), expected)
