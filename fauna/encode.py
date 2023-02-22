from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any

from iso8601 import parse_date

from fauna.models import DocumentReference, Module


def _int(obj: int):
    if -2**31 + 1 <= obj <= 2**31 - 1:
        return {"@int": repr(obj)}
    elif -2**63 + 1 <= obj <= 2**63 - 1:
        return {"@long": repr(obj)}
    else:
        raise ValueError("Precision loss when converting int to Fauna type")


def _bool(obj: bool):
    return obj


def _float(obj: float):
    return {"@double": repr(obj)}


def _str(obj: str):
    return obj


def _datetime(obj: datetime):
    return {"@time": obj.isoformat(sep="T")}


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
    if type(obj) in _encoder_map:
        return _encoder_map[type(obj)](obj)
    elif isinstance(obj, dict):
        _out = {k: encode_to_typed(v) for k, v in obj.items()}
        if any(i.startswith("@") for i in obj.keys()):
            return _obj(_out)
        return _out
    else:
        try:
            iterable = iter(obj)
            return [encode_to_typed(i) for i in iterable]
        except Exception as e:
            raise ValueError(
                "Object {} of type {} cannot be encoded".format(
                    obj, type(obj)), None) from e


def decode_from_json(value: str):
    return json.loads(value, object_hook=_decode_hook)


def _decode_hook(dct: dict):

    try:
        if "@int" in dct:
            i = dct["@int"]
            if not isinstance(i, int):
                return int(i)
        if "@long" in dct:
            j = dct["@long"]
            if not isinstance(j, int):
                return int(j)
        if "@double" in dct:
            d = dct["@double"]
            if not isinstance(d, float):
                return float(d)
        if "@object" in dct:
            return dct["@object"]
        if "@mod" in dct:
            m = dct["@mod"]
            if not isinstance(m, Module):
                return Module(m)
        if "@time" in dct:
            t = dct["@time"]
            if not isinstance(t, datetime):
                return parse_date(t)
        if "@date" in dct:
            dt = dct["@date"]
            if not isinstance(dt, date):
                return parse_date(dt).date()
        if "@doc" in dct:
            doc = dct["@doc"]
            if not isinstance(doc, DocumentReference):
                return DocumentReference.from_string(doc)
    except:
        # band-aid to handle scenarios where users have conflicting fields that don't match the type
        pass

    return dct
