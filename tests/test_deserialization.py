from unittest import TestCase
from iso8601 import parse_date

from faunadb._json import parse_json


def test_fauna_time(snapshot):
    assert parse_json('{"@time":"1970-01-01T00:00:00.123456789Z"}') == snapshot


def test_date(snapshot):
    assert parse_json('{"@date":"1970-01-01"}') == snapshot


def test_string(snapshot):
    assert parse_json('"a string"') == snapshot


def test_number(snapshot):
    assert parse_json('1') == snapshot
    assert parse_json('3.14') == snapshot


def test_empty_array(snapshot):
    assert parse_json('[]') == snapshot


# class DeserializationTest(TestCase):

#     def test_array(self):
#         self.assertJson('[1, "a string"]', [1, "a string"])
#         self.assertJson(
#             """[
#                       {"@ref":{"id":"widgets","collection":{"@ref":{"id":"collections"}}}},
#                       {"@date":"1970-01-01"}
#                     ]""", [
#                 Ref("widgets", Native.COLLECTIONS),
#                 parse_date("1970-01-01").date()
#             ])

#     def test_empty_object(self):
#         self.assertJson('{}', {})

#     def test_object(self):
#         self.assertJson('{"key":"value"}', {"key": "value"})

#     def test_object_literal(self):
#         self.assertJson('{"@obj":{"@name":"John"}}', {"@name": "John"})

#     def test_complex_object(self):
#         self.maxDiff = None
#         json = """{
#       "ref": {"@ref":{"collection":{"@ref":{"id":"collections"}},"id":"widget"}},
#       "set_ref": {"@set":{"match":{"@ref":{"collection":{"@ref":{"id":"collections"}},"id":"widget"}},"terms":"Laptop"}},
#       "date": {"@date":"1970-01-01"},
#       "time": {"@ts":"1970-01-01T00:00:00.123456789Z"},
#       "object": {"@obj":{"key":"value"}},
#       "array": [1, 2],
#       "string": "a string",
#       "number": 1
#     }"""

#         self.assertJson(
#             json, {
#                 "ref":
#                 Ref("widget", Native.COLLECTIONS),
#                 "set_ref":
#                 SetRef({
#                     "match": Ref("widget", Native.COLLECTIONS),
#                     "terms": "Laptop"
#                 }),
#                 "date":
#                 parse_date("1970-01-01").date(),
#                 "time":
#                 FaunaTime("1970-01-01T00:00:00.123456789Z"),
#                 "object": {
#                     "key": "value"
#                 },
#                 "array": [1, 2],
#                 "string":
#                 "a string",
#                 "number":
#                 1
#             })

#     def assertJson(self, json, expected):
#         self.assertEqual(parse_json(json), expected)
