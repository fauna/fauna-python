import json

from fauna.encode import encode_to_typed, decode_from_json
from fixtures.all_types import fixture_untyped, fixture_typed_string, fixture_typed
from fixtures.tag_conflicts import conflicts_with_built_ins, conflicts_with_built_ins_typed_json, \
    conflicts_with_built_ins_typed, conflicts_with_fauna, conflicts_with_fauna_typed_json, conflicts_with_fauna_typed, \
    conflicts_with_object, conflicts_with_object_typed, conflicts_with_object_typed_json, nested_conflicts, \
    nested_conflicts_typed, nested_conflicts_typed_json


def test_encode_model():
    res = encode_to_typed(fixture_untyped)
    assert res == fixture_typed
    json_str = json.dumps(res)
    assert json_str == fixture_typed_string


def test_decode_from_json():
    res = decode_from_json(fixture_typed_string)
    _deep_diff(res, fixture_untyped)
    _deep_diff(fixture_untyped, res)


def test_encode_conflicts_with_built_ins():
    res = encode_to_typed(conflicts_with_built_ins)
    assert res == conflicts_with_built_ins_typed
    json_str = json.dumps(res)
    assert json_str == conflicts_with_built_ins_typed_json


def test_decode_conflicts_with_built_ins():
    res = decode_from_json(conflicts_with_built_ins_typed_json)
    _deep_diff(res, conflicts_with_built_ins)
    _deep_diff(conflicts_with_built_ins, res)


def test_encode_conflicts_with_fauna():
    res = encode_to_typed(conflicts_with_fauna)
    assert res == conflicts_with_fauna_typed
    json_str = json.dumps(res)
    assert json_str == conflicts_with_fauna_typed_json


def test_decode_conflicts_with_fauna():
    res = decode_from_json(conflicts_with_fauna_typed_json)
    _deep_diff(res, conflicts_with_fauna)
    _deep_diff(conflicts_with_fauna, res)


def test_encode_conflicts_with_object():
    res = encode_to_typed(conflicts_with_object)
    assert res == conflicts_with_object_typed
    json_str = json.dumps(res)
    assert json_str == conflicts_with_object_typed_json


# TODO(BT-3550): this doesn't work yet
# def test_decode_conflicts_with_object():
#     res = decode_from_json(conflicts_with_object_typed_json)
#     _deep_diff(res, conflicts_with_object)
#     _deep_diff(conflicts_with_object, res)


def test_encode_nested_conflicts():
    res = encode_to_typed(nested_conflicts)
    assert res == nested_conflicts_typed


def test_decode_nested_conflicts():
    res = decode_from_json(nested_conflicts_typed_json)
    _deep_diff(res, nested_conflicts)
    _deep_diff(nested_conflicts, res)


def _deep_diff(obj1, obj2):
    assert isinstance(obj2, type(obj1))
    for k, v in obj1.items():
        assert isinstance(obj2[k], type(v))

        if isinstance(v, dict):
            _deep_diff(v, obj2[k])

        assert _str_rep(k, obj2[k]) == _str_rep(k, v)


def _str_rep(k, v):
    return f"{str(k)}:{str(v)}"
