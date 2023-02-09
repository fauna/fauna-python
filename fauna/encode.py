from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any, Mapping, Sequence

from iso8601 import parse_date

from fauna.models import DocumentReference, Module


def _int(obj: int):
    if -2 ** 31 + 1 <= obj <= 2 ** 31 - 1:
        return {"@int": repr(obj)}
    elif -2 ** 63 + 1 <= obj <= 2 ** 63 - 1:
        return {"@long": repr(obj)}
    else:
        raise ValueError(
            "Precision loss when converting int to Fauna type")


def _bool(obj: bool):
    return {"@bool": repr(obj)}


def _float(obj: float):
    return {"@double": repr(obj)}


def _str(obj: str):
    return obj


def _datetime(obj: datetime):
    return {"@time": obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}


def _date(obj: date):
    return {"@date": obj.isoformat()}


def _doc_ref(obj: DocumentReference):
    return {"@doc": str(obj)}


def _mod(obj: Module):
    return {"@mod": str(obj)}


def _obj(obj: Any):
    return {"@object": obj}


_encoder_map = {
    int: _int,
    bool: _bool,
    float: _float,
    str: _str,
    datetime: _datetime,
    date: _date,
    DocumentReference: _doc_ref,
    Module: _mod,
}


def encode_to_typed(obj: Any) -> Any:
    return _encode_to_typed(obj)


def _encode_to_typed(obj: Any) -> Mapping[str, Any] | str | Sequence[Mapping[str, Any] | str | None]:
    if type(obj) in _encoder_map:
        return _encoder_map[type(obj)](obj)
    elif isinstance(obj, dict):
        _out = {k: _encode_to_typed(v) for k, v in obj.items()}
        if any(i.startswith("@") for i in obj.keys()):
            return _obj(_out)
        return _out
    else:
        try:
            iterable = iter(obj)
            return [_encode_to_typed(i) for i in iterable]
        except Exception as e:
            raise ValueError(
                "Object {} of type {} cannot be encoded".format(obj, type(obj)), None) from e


def decode_from_json(value: str):
    return json.loads(value, object_hook=_decode_hook)


def _decode_hook(dct: dict):
    if "@bool" in dct:
        return dct["@bool"] in ['true', 'True', 1, True]
    if "@int" in dct:
        return int(dct["@int"])
    if "@long" in dct:
        return int(dct["@long"])
    if "@double" in dct:
        return float(dct["@double"])
    if "@object" in dct:
        return dct["@object"]
    if "@mod" in dct:
        return Module(dct["@mod"])
    if "@time" in dct:
        return parse_date(dct["@time"])
    if "@date" in dct:
        return parse_date(dct["@date"]).date()
    if "@doc" in dct:
        return DocumentReference.from_string(dct["@doc"])

    return dct
