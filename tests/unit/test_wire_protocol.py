from datetime import date, datetime, timezone, timedelta
from typing import Any

import pytest

from fauna import Document, DocumentReference, Module, NamedDocumentReference, NamedDocument
from fauna.wire_protocol import FaunaEncoder, FaunaDecoder


def test_encode_decode_primitives(subtests):
    with subtests.test(msg="encode string"):
        test = "hello"
        encoded = FaunaEncoder.encode(test)
        assert test == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode true"):
        test = True
        encoded = FaunaEncoder.encode(test)
        assert test == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode false"):
        test = False
        encoded = FaunaEncoder.encode(test)
        assert test == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode int into @int"):
        test = 10
        encoded = FaunaEncoder.encode(test)
        assert {"@int": "10"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode max 32-bit signed int into @int"):
        test = 2147483647
        encoded = FaunaEncoder.encode(test)
        assert {"@int": "2147483647"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode min 32-bit signed int into @int"):
        test = -2147483648
        encoded = FaunaEncoder.encode(test)
        assert {"@int": "-2147483648"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode max 32-bit signed int + 1 into @long"):
        test = 2147483648
        encoded = FaunaEncoder.encode(test)
        assert {"@long": "2147483648"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode min 32-bit signed int - 1 into @long"):
        test = -2147483649
        encoded = FaunaEncoder.encode(test)
        assert {"@long": "-2147483649"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode max 64-bit signed int into @long"):
        test = 9223372036854775807
        encoded = FaunaEncoder.encode(test)
        assert {"@long": "9223372036854775807"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode min 64-bit signed int into @long"):
        test = -9223372036854775808
        encoded = FaunaEncoder.encode(test)
        assert {"@long": "-9223372036854775808"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode max 64-bit signed int + 1 throws error"):
        test = 9223372036854775808
        with pytest.raises(
                ValueError,
                match="Precision loss when converting int to Fauna type"):
            FaunaEncoder.encode(test)

    with subtests.test(msg="encode min 64-bit signed int -1 throws error"):
        test = -9223372036854775809
        with pytest.raises(
                ValueError,
                match="Precision loss when converting int to Fauna type"):
            FaunaEncoder.encode(test)

    with subtests.test(msg="encode negative float into @double"):
        test = -100.0
        encoded = FaunaEncoder.encode(test)
        assert {"@double": "-100.0"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode positive float into @double"):
        test = 9.999999999999
        encoded = FaunaEncoder.encode(test)
        assert {"@double": "9.999999999999"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode None into None"):
        test = {"foo": None}
        encoded = FaunaEncoder.encode(test)
        assert test == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_dates_times(subtests):
    with subtests.test(msg="encode date into @date"):
        test = date(2023, 2, 28)
        encoded = FaunaEncoder.encode(test)
        assert {"@date": "2023-02-28"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode datetime into @time"):
        test = datetime(2023,
                        2,
                        28,
                        10,
                        10,
                        10,
                        10,
                        tzinfo=timezone(timedelta(0), '+00:00'))
        encoded = FaunaEncoder.encode(test)
        assert {"@time": "2023-02-28T10:10:10.000010+00:00"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="datetimes without tzinfo raise ValueError"):
        test = datetime(2023, 2, 2)
        with pytest.raises(ValueError,
                           match="datetimes must be timezone-aware"):
            FaunaEncoder.encode(test)


def test_encode_document_references(subtests):
    doc_ref = DocumentReference.from_string("Col:123")
    with subtests.test(msg="encode/decode with @doc"):
        encoded = FaunaEncoder.encode(doc_ref)
        assert {'@ref': {'coll': {'@mod': 'Col'}, 'id': 123}} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert doc_ref == decoded

    with subtests.test(msg="decode doc ref from @ref"):
        test = {"@ref": {"id": "123", "coll": {"@mod": "Col"}}}
        decoded = FaunaDecoder.decode(test)
        assert doc_ref == decoded


def test_encode_named_document_references(subtests):
    doc_ref = NamedDocumentReference("Col", "Hi")
    with subtests.test(msg="encode/decode with @doc"):
        encoded = FaunaEncoder.encode(doc_ref)
        assert {"@ref": {"name": "Hi", "coll": {"@mod": "Col"}}} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert doc_ref == decoded

    with subtests.test(msg="decode doc ref from @ref"):
        test = {"@ref": {"name": "Hi", "coll": {"@mod": "Col"}}}
        decoded = FaunaDecoder.decode(test)
        assert doc_ref == decoded


def test_encode_documents(subtests):
    with subtests.test(msg="encode/decode document"):
        test = Document({"id": "123", "coll": Module("Dogs"), "name": "Scout"})
        encoded = FaunaEncoder.encode(test)
        # should encode to a ref!
        assert {"@ref": {"id": "123", "coll": {"@mod": "Dogs"}}} == encoded
        decoded = FaunaDecoder.decode(encoded)
        # refs will decode into references, not Documents
        assert DocumentReference("Dogs", 123) == decoded

    with subtests.test(msg="decode document with id and name"):
        encoded = {
            "@doc": {
                "id": 123,
                "coll": {
                    "@mod": "Dogs"
                },
                "name": "Scout"
            }
        }
        decoded = FaunaDecoder.decode(encoded)
        # refs will decode into references, not Documents
        assert Document({
            "id": 123,
            "coll": Module("Dogs"),
            "name": "Scout"
        }) == decoded


def test_encode_named_documents(subtests):
    with subtests.test(msg="encode/decode named document"):
        test = NamedDocument({"name": "DogSchema", "coll": Module("Dogs")})
        encoded = FaunaEncoder.encode(test)
        # should encode to a ref!
        assert {
            "@ref": {
                "name": "DogSchema",
                "coll": {
                    "@mod": "Dogs"
                }
            }
        } == encoded
        decoded = FaunaDecoder.decode(encoded)
        # refs will decode into references, not Documents
        assert NamedDocumentReference("Dogs", "DogSchema") == decoded


def test_encode_modules(subtests):
    with subtests.test(msg="encode module into @mod"):
        test = Module("Math")
        encoded = FaunaEncoder.encode(test)
        assert {"@mod": "Math"} == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_sets(subtests):
    with subtests.test(msg="unwrap @set"):
        test = {"@set": {}}
        decoded = FaunaDecoder.decode(test)
        assert decoded == {}


def test_encode_collections(subtests):
    test_dict = {
        "int":
        10,
        "double":
        10.0,
        "long":
        2147483649,
        "string":
        "foo",
        "true":
        True,
        "false":
        False,
        "none":
        None,
        "date":
        date(2023, 2, 28),
        "time":
        datetime(2023,
                 2,
                 28,
                 10,
                 10,
                 10,
                 10,
                 tzinfo=timezone(timedelta(0), '+00:00')),
    }

    encoded_dict = {
        "int": {
            "@int": "10"
        },
        "double": {
            "@double": "10.0"
        },
        "long": {
            "@long": "2147483649"
        },
        "string": "foo",
        "true": True,
        "false": False,
        "none": None,
        "date": {
            "@date": "2023-02-28"
        },
        "time": {
            "@time": "2023-02-28T10:10:10.000010+00:00"
        },
    }

    with subtests.test(msg="encode dict into dict"):
        encoded = FaunaEncoder.encode(test_dict)
        assert encoded_dict == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test_dict == decoded

    with subtests.test(msg="encode list into list"):
        test = list(test_dict.values())
        expected = list(encoded_dict.values())
        encoded = FaunaEncoder.encode(test)
        assert expected == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="encode tuple into list"):
        test = tuple(test_dict.values())
        expected = list(encoded_dict.values())
        encoded = FaunaEncoder.encode(test)
        assert expected == encoded
        decoded = FaunaDecoder.decode(encoded)
        assert list(test_dict.values()) == decoded


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

    with subtests.test(msg="@int conflict with int type"):
        test = {"@int": 10}
        expected = {"@object": {"@int": {"@int": "10"}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@int conflict with other type"):
        test = {"@int": "bar"}
        expected = {"@object": {"@int": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_long_conflicts(subtests):

    with subtests.test(msg="@long conflict with long type"):
        test = {"@long": 2147483649}
        expected = {"@object": {"@long": {"@long": "2147483649"}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@long conflict with other type"):
        test = {"@long": "bar"}
        expected = {"@object": {"@long": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_float_conflicts(subtests):

    with subtests.test(msg="@double conflict with float type"):
        test = {"@double": 10.2}
        expected = {"@object": {"@double": {"@double": "10.2"}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@double conflict with other type"):
        test = {"@double": "bar"}
        expected = {"@object": {"@double": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_date_time_conflicts(subtests):

    with subtests.test(msg="@date conflict with date type"):
        test = {"@date": date(2023, 2, 28)}
        expected = {"@object": {"@date": {"@date": "2023-02-28"}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@date conflict with other type"):
        test = {"@date": "bar"}
        expected = {"@object": {"@date": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@time conflict with date type"):
        test = {
            "@time":
            datetime(2023,
                     2,
                     28,
                     10,
                     10,
                     10,
                     10,
                     tzinfo=timezone(timedelta(0), '+00:00'))
        }
        expected = {
            "@object": {
                "@time": {
                    "@time": "2023-02-28T10:10:10.000010+00:00"
                }
            }
        }
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@time conflict with other type"):
        test = {"@time": "bar"}
        expected = {"@object": {"@time": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_fauna_type_conflicts(subtests):

    with subtests.test(msg="@ref conflict with ref type"):
        test = {"@ref": DocumentReference.from_string("Col:123")}
        expected = {
            "@object": {
                "@ref": {
                    "@ref": {
                        "id": 123,
                        "coll": {
                            "@mod": "Col"
                        }
                    }
                }
            }
        }
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@doc conflict with other type"):
        test = {"@doc": "bar"}
        expected = {"@object": {"@doc": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@mod conflict with mod type"):
        test = {"@mod": Module("Math")}
        expected = {"@object": {"@mod": {"@mod": "Math"}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@mod conflict with other type"):
        test = {"@mod": "bar"}
        expected = {"@object": {"@mod": "bar"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_object_conflicts(subtests):

    with subtests.test(msg="@object conflicts with type"):
        test = {"@object": 10}
        expected = {"@object": {"@object": {"@int": "10"}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@object conflicts with @int"):
        test = {"@object": {"@int": "bar"}}
        expected = {"@object": {"@object": {"@object": {"@int": "bar"}}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="@object conflicts with @object"):
        test = {"@object": {"@object": "bar"}}
        expected = {"@object": {"@object": {"@object": {"@object": "bar"}}}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_multiple_keys_in_conflict(subtests):

    with subtests.test(msg="conflict with other non-conflicting keys"):
        test = {"@int": "foo", "tree": "birch"}
        expected = {"@object": {"@int": "foo", "tree": "birch"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="conflict with other conflicting keys"):
        test = {"@int": "foo", "@double": "birch"}
        expected = {"@object": {"@int": "foo", "@double": "birch"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_nested_conflict(subtests):

    with subtests.test(msg="nested conflicts"):
        test = {"@int": {"@date": {"@time": {"@long": 10}}}}
        expected = {
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
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_non_conflicting_at_prefix(subtests):

    with subtests.test(msg="non-conflicting @ prefix"):
        test = {"@foo": 10}
        expected = {"@foo": {"@int": "10"}}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded


def test_encode_complex_objects(subtests, complex_untyped_object,
                                complex_typed_object):

    with subtests.test(msg="reasonable complex object"):
        encoded = FaunaEncoder.encode(complex_untyped_object)
        assert encoded == complex_typed_object
        decoded = FaunaDecoder.decode(encoded)
        assert complex_untyped_object == decoded

    with subtests.test(msg="large list"):
        test: Any = [10] * 10000
        expected = [{"@int": "10"}] * 10000
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    with subtests.test(msg="large dict"):
        test = {f"k{str(k)}": k for k in range(1, 10000)}
        expected = {f"k{str(k)}": {"@int": str(k)} for k in range(1, 10000)}
        encoded = FaunaEncoder.encode(test)
        assert encoded == expected
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded

    # TODO(lucas): Fix max recursion bug to support deeper nesting
    with subtests.test(msg="deep nesting in dict"):
        test: Any = {"k1": "v"}
        cur_node = test
        for i in range(2, 300):
            node: dict[str, Any] = {f"k{i}": "v"}
            cur_node[f"k{i}"] = node
            cur_node = node

        encoded = FaunaEncoder.encode(test)
        assert encoded == test
        decoded = FaunaDecoder.decode(encoded)
        assert test == decoded
