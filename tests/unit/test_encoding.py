import re
from datetime import date, datetime, timezone, timedelta
from typing import Any

import pytest

from fauna import fql
from fauna.encoding import FaunaEncoder, FaunaDecoder
from fauna.query.models import DocumentReference, NamedDocumentReference, Document, NamedDocument, Module, Page, \
    NullDocument

fixed_datetime = datetime.fromisoformat("2023-03-17T00:00:00+00:00")


def test_encode_primitives(subtests):
  with subtests.test(msg="encode string"):
    test = "hello"
    encoded = FaunaEncoder.encode(test)
    assert {"value": test} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode true"):
    test = True
    encoded = FaunaEncoder.encode(test)
    assert {"value": test} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode false"):
    test = False
    encoded = FaunaEncoder.encode(test)
    assert {"value": test} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode int into @int"):
    test = 10
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@int": "10"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode max 32-bit signed int into @int"):
    test = 2147483647
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@int": "2147483647"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode min 32-bit signed int into @int"):
    test = -2147483648
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@int": "-2147483648"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode max 32-bit signed int + 1 into @long"):
    test = 2147483648
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@long": "2147483648"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode min 32-bit signed int - 1 into @long"):
    test = -2147483649
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@long": "-2147483649"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode max 64-bit signed int into @long"):
    test = 9223372036854775807
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@long": "9223372036854775807"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode min 64-bit signed int into @long"):
    test = -9223372036854775808
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@long": "-9223372036854775808"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode max 64-bit signed int + 1 throws error"):
    test = 9223372036854775808
    with pytest.raises(
        ValueError, match="Precision loss when converting int to Fauna type"):
      FaunaEncoder.encode(test)

  with subtests.test(msg="encode min 64-bit signed int -1 throws error"):
    test = -9223372036854775809
    with pytest.raises(
        ValueError, match="Precision loss when converting int to Fauna type"):
      FaunaEncoder.encode(test)

  with subtests.test(msg="encode negative float into @double"):
    test = -100.0
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@double": "-100.0"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode positive float into @double"):
    test = 9.999999999999
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@double": "9.999999999999"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode None into None"):
    test = {"foo": None}
    encoded = FaunaEncoder.encode(test)
    assert {"object": {"foo": {"value": None}}} == encoded
    decoded = FaunaDecoder.decode({"foo": None})
    assert test == decoded


def test_encode_dates_times(subtests):
  with subtests.test(msg="encode date into @date"):
    test = date(2023, 2, 28)
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@date": "2023-02-28"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="encode datetime into @time"):
    test = datetime(
        2023, 2, 28, 10, 10, 10, 1, tzinfo=timezone(timedelta(0), '+00:00'))
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@time": "2023-02-28T10:10:10.000001+00:00"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded

  with subtests.test(msg="datetimes without tzinfo raise ValueError"):
    test = datetime(2023, 2, 2)
    with pytest.raises(ValueError, match="datetimes must be timezone-aware"):
      FaunaEncoder.encode(test)


def test_encode_document_references(subtests):
  doc_ref = DocumentReference.from_string("Col:123")
  with subtests.test(msg="encode/decode with @doc"):
    encoded = FaunaEncoder.encode(doc_ref)
    assert {'value': {'@ref': {'coll': {'@mod': 'Col'}, 'id': "123"}}} == encoded
    decoded = FaunaDecoder.decode(encoded['value'])
    assert doc_ref == decoded

  with subtests.test(msg="decode doc ref from @ref"):
    test = {"@ref": {"id": "123", "coll": {"@mod": "Col"}}}
    decoded = FaunaDecoder.decode(test)
    assert doc_ref == decoded


def test_null_docments(subtests):
  with subtests.test(msg="encode null doc"):
    null_doc = NullDocument(DocumentReference("NDCol", "456"), "not found")
    expected = {"value": {"@ref": {"id": "456", "coll": {"@mod": "NDCol"}}}}
    encoded = FaunaEncoder.encode(null_doc)
    assert expected == encoded

  with subtests.test(msg="decode null doc"):
    null_doc = NullDocument(DocumentReference("NDCol", "456"), "not found")
    test = {
        "@ref": {
            "id": "456",
            "coll": {
                "@mod": "NDCol"
            },
            "exists": False,
            "cause": "not found"
        }
    }
    decoded = FaunaDecoder.decode(test)
    assert null_doc == decoded

  with subtests.test(msg="encode named null doc"):
    null_doc = NullDocument(
        NamedDocumentReference("Collection", "Party"), "not found")
    expected = {"value": {"@ref": {"name": "Party", "coll": {"@mod": "Collection"}}}}
    encoded = FaunaEncoder.encode(null_doc)
    assert expected == encoded

  with subtests.test(msg="decode named null doc"):
    null_doc = NullDocument(
        NamedDocumentReference("Collection", "Party"), "not found")
    test = {
        "@ref": {
            "name": "Party",
            "coll": {
                "@mod": "Collection"
            },
            "exists": False,
            "cause": "not found"
        }
    }
    decoded = FaunaDecoder.decode(test)
    assert null_doc == decoded


def test_encode_named_document_references(subtests):
  doc_ref = NamedDocumentReference("Col", "Hi")
  with subtests.test(msg="encode/decode with @doc"):
    encoded = FaunaEncoder.encode(doc_ref)
    assert {"value": {"@ref": {"name": "Hi", "coll": {"@mod": "Col"}}}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert doc_ref == decoded

  with subtests.test(msg="decode doc ref from @ref"):
    test = {"@ref": {"name": "Hi", "coll": {"@mod": "Col"}}}
    decoded = FaunaDecoder.decode(test)
    assert doc_ref == decoded


def test_encode_documents(subtests):
  with subtests.test(msg="encode/decode document"):
    test = Document(
        id="123", coll="Dogs", ts=fixed_datetime, data={"name": "Scout"})
    encoded = FaunaEncoder.encode(test)
    # should encode to a ref!
    assert {"value": {"@ref": {"id": "123", "coll": {"@mod": "Dogs"}}}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    # refs will decode into references, not Documents
    assert DocumentReference("Dogs", "123") == decoded

  with subtests.test(msg="decode document with id and name"):
    test = {
        "@doc": {
            "id": "123",
            "coll": {
                "@mod": "Dogs"
            },
            "ts": {
                "@time": fixed_datetime.isoformat(),
            },
            "name": "Scout"
        }
    }
    decoded = FaunaDecoder.decode(test)
    assert Document(
        id="123", coll="Dogs", ts=fixed_datetime,
        data={"name": "Scout"}) == decoded


def test_encode_named_documents(subtests):
  with subtests.test(msg="encode/decode named document"):
    test = NamedDocument(name="DogSchema", coll="Dogs", ts=fixed_datetime)
    encoded = FaunaEncoder.encode(test)
    # should encode to a ref!
    assert {"value": {"@ref": {"name": "DogSchema", "coll": {"@mod": "Dogs"}}}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    # refs will decode into references, not Documents
    assert NamedDocumentReference("Dogs", "DogSchema") == decoded

  with subtests.test(msg="decode named document"):
    test = {
        "@doc": {
            "coll": {
                "@mod": "Dogs"
            },
            "ts": {
                "@time": fixed_datetime.isoformat(),
            },
            "name": "Scout",
            "other": "data",
        }
    }
    decoded = FaunaDecoder.decode(test)
    assert NamedDocument(
        name="Scout", coll="Dogs", ts=fixed_datetime,
        data={"other": "data"}) == decoded


def test_encode_modules(subtests):
  with subtests.test(msg="encode module into @mod"):
    test = Module("Math")
    encoded = FaunaEncoder.encode(test)
    assert {"value": {"@mod": "Math"}} == encoded
    decoded = FaunaDecoder.decode(encoded["value"])
    assert test == decoded


def test_decode_sets(subtests):
  with subtests.test(msg="decode @set into page"):
    test = {"@set": {"data": [1, 2], "after": "asdflkj"}}
    decoded = FaunaDecoder.decode(test)
    assert decoded == Page(data=[1, 2], after="asdflkj")

  with subtests.test(msg="decode @set into page with no after token"):
    test = {"@set": {"data": [1, 2]}}
    decoded = FaunaDecoder.decode(test)
    assert decoded == Page(data=[1, 2])

  with subtests.test(msg="decode @set string into page"):
    test = {"@set": "lkjlkj"}
    decoded = FaunaDecoder.decode(test)
    assert decoded == Page(after="lkjlkj")

  with subtests.test(msg="encoding Page raises error"):
    p = Page()
    err = "Object Page() of type <class 'fauna.query.models.Page'> cannot be encoded"
    with pytest.raises(ValueError, match=re.escape(err)):
      FaunaEncoder.encode(p)


def test_encode_with_circular_references(subtests):

  with subtests.test(msg="circular reference with dict"):
    test: dict[str, Any] = {"foo": "bar"}
    test["self"] = test

    with pytest.raises(ValueError, match="Circular reference detected"):
      FaunaEncoder.encode(test)

  with subtests.test(msg="circular reference with list"):
    lst: list[Any] = ["1", "2"]
    lst.append(lst)

    with pytest.raises(ValueError, match="Circular reference detected"):
      FaunaEncoder.encode(lst)


def test_encode_int_conflicts(subtests):

  with subtests.test(msg="encode @int conflict with int type"):
    test = {"@int": 10}
    expected = {"object": {"@int": {"value": {"@int": "10"}}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="encode @int conflict with other type"):
    test = {"@int": "bar"}
    expected = {"object": {"@int": {"value": "bar"}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="decode @int conflict with int type"):
    test = {"@object": {"@int": "10"}}
    decoded = FaunaDecoder.decode(test)
    assert {"@int": "10"} == decoded

  with subtests.test(msg="decode @int conflict with other type"):
    test = {"@object": {"@int": "bar"}}
    decoded = FaunaDecoder.decode(test)
    assert {"@int": "bar"} == decoded


def test_encode_long_conflicts(subtests):

  with subtests.test(msg="encode @long conflict with long type"):
    test = {"@long": 2147483649}
    expected = {"object": {"@long": {"value": {"@long": "2147483649"}}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="encode @long conflict with other type"):
    test = {"@long": "bar"}
    expected = {"object": {"@long": {"value": "bar"}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected


  with subtests.test(msg="decode @long conflict with long type"):
    expected = {"@long": 2147483649}
    test = {"@object": {"@long": {"@long": "2147483649"}}}
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded

  with subtests.test(msg="decode @long conflict with other type"):
    expected = {"@long": "bar"}
    test = {"@object": {"@long": "bar"}}
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded


def test_encode_float_conflicts(subtests):

  with subtests.test(msg="encode @double conflict with double type"):
    test = {"@double": 10.2}
    expected = {"object": {"@double": {"value": {"@double": "10.2"}}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="encode @double conflict with other type"):
    test = {"@double": "bar"}
    expected = {"object": {"@double": {"value": "bar"}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="decode @double conflict with double type"):
    expected = {"@double": 10.2}
    test = {"@object": {"@double": {"@double": "10.2"}}}
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded

  with subtests.test(msg="decode @double conflict with other type"):
    expected = {"@double": "bar"}
    test = {"@object": {"@double": "bar"}}
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded


def test_encode_date_time_conflicts(subtests):

  with subtests.test(msg="encode @date conflict with date type"):
    test = {"@date": date(2023, 2, 28)}
    expected = {"object": {"@date": {"value": {"@date": "2023-02-28"}}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="encode @date conflict with other type"):
    test = {"@date": "bar"}
    expected = {"object": {"@date": {"value": "bar"}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="decode @date conflict with date type"):
    test = {"@object": {"@date": {"@date": "2023-02-28"}}}
    decoded = FaunaDecoder.decode(test)
    assert {"@date": date(2023, 2, 28)} == decoded

  with subtests.test(msg="decode @date conflict with other type"):
    test =  {"@object": {"@date": "bar"}}
    decoded = FaunaDecoder.decode(test)
    assert {"@date": "bar"} == decoded

  with subtests.test(msg="encode @time conflict with date type"):
    test = {
        "@time":
            datetime(
                2023,
                2,
                28,
                10,
                10,
                10,
                10,
                tzinfo=timezone(timedelta(0), '+00:00'))
    }
    expected = {
        "object": {
            "@time": {
                "value": {"@time": "2023-02-28T10:10:10.000010+00:00"}
            }
        }
    }

    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="encode @time conflict with other type"):
    test = {"@time": "bar"}
    expected = {"object": {"@time": {"value":"bar"}}}
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="decode @time conflict with date type"):
    expected = {
        "@time":
            datetime(
                2023,
                2,
                28,
                10,
                10,
                10,
                10,
                tzinfo=timezone(timedelta(0), '+00:00'))
    }
    test = {
        "@object": {
            "@time": {
                "@time": "2023-02-28T10:10:10.000010+00:00"
            }
        }
    }
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded

  with subtests.test(msg="@time conflict with other type"):
    test = {"@object": {"@time": "bar"}}
    decoded = FaunaDecoder.decode(test)
    assert {"@time": "bar"} == decoded


def test_decode_fauna_type_conflicts(subtests):

  with subtests.test(msg="decode @ref conflict with ref type"):
    test = {"@ref": DocumentReference.from_string("Col:123")}
    typed = {
        "@object": {
            "@ref": {
                "@ref": {
                    "id": "123",
                    "coll": {
                        "@mod": "Col"
                    }
                }
            }
        }
    }
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded

  with subtests.test(msg="@doc conflict with other type"):
    test = {"@doc": "bar"}
    typed = {"@object": {"@doc": "bar"}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded

  with subtests.test(msg="@mod conflict with mod type"):
    test = {"@mod": Module("Math")}
    typed = {"@object": {"@mod": {"@mod": "Math"}}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded

  with subtests.test(msg="@mod conflict with other type"):
    test = {"@mod": "bar"}
    typed = {"@object": {"@mod": "bar"}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded


def test_decode_object_conflicts(subtests):

  with subtests.test(msg="@object conflicts with type"):
    test = {"@object": 10}
    typed = {"@object": {"@object": {"@int": "10"}}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded

  with subtests.test(msg="@object conflicts with @int"):
    test = {"@object": {"@int": "bar"}}
    typed = {"@object": {"@object": {"@object": {"@int": "bar"}}}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded

  with subtests.test(msg="@object conflicts with @object"):
    test = {"@object": {"@object": "bar"}}
    typed = {"@object": {"@object": {"@object": {"@object": "bar"}}}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded


def test_encode_multiple_keys_in_conflict(subtests):

  with subtests.test(msg="conflict with other non-conflicting keys"):
    test = {"@int": "foo", "tree": "birch"}
    typed = {"@object": {"@int": "foo", "tree": "birch"}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded

  with subtests.test(msg="conflict with other conflicting keys"):
    test = {"@int": "foo", "@double": "birch"}
    typed = {"@object": {"@int": "foo", "@double": "birch"}}
    decoded = FaunaDecoder.decode(typed)
    assert test == decoded


def test_encode_nested_conflict(subtests):

  with subtests.test(msg="encode nested conflicts"):
    test = {"@int": {"@date": {"@time": {"@long": 10}}}}
    expected = {
        "object": {
            "@int": {
                "object": {
                    "@date": {
                        "object": {
                            "@time": {
                                "object": {
                                    "@long": {
                                        "value": {"@int": "10"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="decode nested conflicts"):
    expected = {"@int": {"@date": {"@time": {"@long": 10}}}}
    test = {
        "@object": {
            "@int": {
                "@object": {
                    "@date": {
                        "@object": {
                            "@time": {
                                "@object": {
                                    "@long": {
                                        "@int": "10"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded

def test_encode_non_conflicting_at_prefix(subtests):

  with subtests.test(msg="encode non-conflicting @ prefix"):
    test = {"@foo": 10}
    expected = {
        "object": {
            "@foo": {"value": {"@int": "10"}}
        }
    }
    encoded = FaunaEncoder.encode(test)
    assert encoded == expected

  with subtests.test(msg="decode non-conflicting @ prefix"):
    expected = {"@foo": 10}
    test = {"@foo": {"@int": "10"}}
    decoded = FaunaDecoder.decode(test)
    assert expected == decoded


def test_encode_complex_objects(
        subtests,
        complex_untyped_object,
        complex_typed_object,
        complex_wire_encoded_object,
):
  with subtests.test(msg="encode array with nesting"):
    doc_ref = DocumentReference.from_string("Array:123")
    test = [1, ["hi"], doc_ref, fql("let d = ${foo}", foo=[{'inner': 3.1}]), {"foo": {"bar": 123}}]
    expected = {
      'array': [
          {'value': {'@int': '1'}},
          {'array': [{'value': 'hi'}]},
          {'value': {'@ref': {'coll': {'@mod': 'Array'}, 'id': '123'}}},
          {'fql': ['let d = ', {'array': [{'object': {'inner': {'value': {'@double': '3.1'}}}}]}]},
          {'object': {'foo': {'object': {'bar': {'value': {'@int': '123'}}}}}}
        ]
    }
    encoded = FaunaEncoder.encode(test)
    assert expected == encoded

  with subtests.test(msg="encode reasonable complex object"):
    encoded = FaunaEncoder.encode(complex_untyped_object)
    assert complex_wire_encoded_object == encoded

  with subtests.test(msg="decode reasonable complex object"):
    decoded = FaunaDecoder.decode(complex_typed_object)
    assert complex_untyped_object == decoded

  with subtests.test(msg="encode large list"):
    test: Any = [10] * 10000
    FaunaEncoder.encode(test)

  with subtests.test(msg="decode large list"):
    test = [{"@int": "10"}] * 10000
    FaunaDecoder.decode(test)

  with subtests.test(msg="encode large dict"):
    test = {f"k{str(k)}": k for k in range(1, 10000)}
    FaunaEncoder.encode(test)

  with subtests.test(msg="decode large dict"):
    test = {f"k{str(k)}": {"@int": str(k)} for k in range(1, 10000)}
    FaunaDecoder.decode(test)

  # TODO(lucas): Fix max recursion bug to support deeper nesting
  with subtests.test(msg="encode deep nesting in dict"):
    test: Any = {"k1": "v"}

    cur_node = test
    for i in range(2, 300):
      node: dict[str, Any] = {f"k{i}": "v"}
      cur_node[f"k{i}"] = node
      cur_node = node

    FaunaEncoder.encode(test)

  with subtests.test(msg="decode deep nesting in dict"):
    test: Any = {"k1": "v"}
    cur_node = test
    for i in range(2, 300):
      node: dict[str, Any] = {f"k{i}": "v"}
      cur_node[f"k{i}"] = node
      cur_node = node

    FaunaDecoder.decode(test)

def test_encode_query_builder_strings(subtests):
  with subtests.test(msg="pure string query"):
    actual = FaunaEncoder.encode(fql("let x = 11"))
    expected = {"fql": ["let x = 11"]}
    assert expected == actual

  with subtests.test(msg="pure string query with braces"):
    actual = FaunaEncoder.encode(fql("let x = { y: 11 }"))
    expected = {"fql": ["let x = { y: 11 }"]}
    assert expected == actual


def test_encode_query_builder_with_fauna_string_interpolation():
  qb = fql("let age = ${n1}\n\"Alice is #{age} years old.\"", n1=5)
  actual = FaunaEncoder.encode(qb)
  expected = {
      "fql": [
          "let age = ",
          {
              "value": {
                  "@int": "5"
              }
          },
          "\n\"Alice is #{age} years old.\"",
      ]
  }
  assert expected == actual


def test_encode_query_builder_with_value(subtests):
  with subtests.test(msg="simple value"):
    user = {"name": "Dino", "age": 0, "birthdate": date(2023, 2, 24)}
    qb = fql("""let x = ${my_var}""", my_var=user)
    actual = FaunaEncoder.encode(qb)
    expected = {
        "fql": [
            "let x = ", {
                'object': {
                    'name': {'value': 'Dino'},
                    'age': {
                      'value': {'@int': '0'}
                    },
                    'birthdate': {
                      'value': {'@date': '2023-02-24'}
                    }
                }
            }
        ]
    }

    assert expected == actual


def test_encode_query_builder_sub_queries(subtests):
  with subtests.test(msg="single subquery with object"):
    user = {"name": "Dino", "age": 0, "birthdate": date(2023, 2, 24)}
    inner = fql("let x = ${my_var}", my_var=user)
    outer = fql("${inner}\nx { .name }", inner=inner)
    actual = FaunaEncoder.encode(outer)
    expected = {
        "fql": [{
            "fql": [
                "let x = ", {
                    'object': {
                      'name': {'value': 'Dino'},
                      'age': {
                        'value': {'@int': '0'}
                      },
                      'birthdate': {
                        'value': {'@date': '2023-02-24'}
                      }
                    }
                }
            ]
        }, "\nx { .name }"]
    }

    assert expected == actual
