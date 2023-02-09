import json

from fauna.encode import encode_to_typed, decode_from_json
from fixtures.all_types import fixture_untyped, fixture_typed_string, fixture_typed


def test_typed_format_encodes_to_json():
    res = encode_to_typed(fixture_untyped)
    json_string = json.dumps(res)
    assert json_string == fixture_typed_string


def test_encode_model():
    res = encode_to_typed(fixture_untyped)
    assert res == fixture_typed


def test_decode_from_json():
    res = decode_from_json(fixture_typed_string)
    _deep_diff(res, fixture_untyped)
    _deep_diff(fixture_untyped, res)


def _deep_diff(obj1, obj2):
    assert isinstance(obj2, type(obj1))
    for k, v in obj1.items():
        assert isinstance(obj2[k], type(v))

        if isinstance(v, dict):
            _deep_diff(v, obj2[k])

        assert _str_rep(k, obj2[k]) == _str_rep(k, v)


def _str_rep(k, v):
    return f"{str(k)}:{str(v)}"
