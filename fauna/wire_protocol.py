from datetime import datetime, date
from typing import Any, List, Optional, Set

from iso8601 import parse_date

from fauna.models import DocumentReference, Module

_RESERVED_TAGS = [
    "@int", "@long", "@double", "@date", "@time", "@doc", "@mod", "@object"
]


class FaunaEncoder:
    """Supports the following types:

    +-------------------+---------------+
    | Python            | Fauna Tags    |
    +===================+===============+
    | dict              | @object       |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str               | string        |
    +-------------------+---------------+
    | int 32-bit signed | @int          |
    +-------------------+---------------+
    | int 64-bit signed | @long         |
    +-------------------+---------------+
    | float             | @double       |
    +-------------------+---------------+
    | datetime.datetime | @time         |
    +-------------------+---------------+
    | datetime.date     | @date         |
    +-------------------+---------------+
    | True              | True          |
    +-------------------+---------------+
    | False             | False         |
    +-------------------+---------------+
    | None              | None          |
    +-------------------+---------------+
    | DocumentReference | @doc          |
    +-------------------+---------------+
    | Module            | @mod          |
    +-------------------+---------------+
    """

    @staticmethod
    def encode(obj: Any):
        """Encodes supported objects into the tagged format.

        Examples:
            - Up to 32-bit ints encode to { "@int": "..." }
            - Up to 64-bit ints encode to { "@long": "..." }
            - Floats encode to { "@double": "..." }
            - datetime encodes to { "@time": "..." }
            - date encodes to { "@date": "..." }
            - DocumentReference encodes to { "@doc": "..." }
            - Module encodes to { "@mod": "..." }

        :raises ValueError: If value cannot be encoded, cannot be encoded safely, or there's a circular reference.
        :param obj: the object to decode
        """
        return FaunaEncoder._encode(obj)

    @staticmethod
    def from_int(obj: int):
        if -2**31 <= obj <= 2**31 - 1:
            return {"@int": repr(obj)}
        elif -2**63 <= obj <= 2**63 - 1:
            return {"@long": repr(obj)}
        else:
            raise ValueError(
                "Precision loss when converting int to Fauna type")

    @staticmethod
    def from_bool(obj: bool):
        return obj

    @staticmethod
    def from_float(obj: float):
        return {"@double": repr(obj)}

    @staticmethod
    def from_str(obj: str):
        return obj

    @staticmethod
    def from_datetime(obj: datetime):
        return {"@time": obj.isoformat(sep="T")}

    @staticmethod
    def from_date(obj: date):
        return {"@date": obj.isoformat()}

    @staticmethod
    def from_doc_ref(obj: DocumentReference):
        return {"@doc": str(obj)}

    @staticmethod
    def from_mod(obj: Module):
        return {"@mod": str(obj)}

    @staticmethod
    def from_dict(obj: Any):
        return {"@object": obj}

    @staticmethod
    def from_none():
        return None

    @staticmethod
    def _encode(o: Any, _markers: Optional[Set] = None):
        if _markers is None:
            _markers = set()

        if isinstance(o, str):
            return FaunaEncoder.from_str(o)
        elif o is None:
            return FaunaEncoder.from_none()
        elif o is True:
            return FaunaEncoder.from_bool(o)
        elif o is False:
            return FaunaEncoder.from_bool(o)
        elif isinstance(o, int):
            return FaunaEncoder.from_int(o)
        elif isinstance(o, float):
            return FaunaEncoder.from_float(o)
        elif isinstance(o, Module):
            return FaunaEncoder.from_mod(o)
        elif isinstance(o, DocumentReference):
            return FaunaEncoder.from_doc_ref(o)
        elif isinstance(o, datetime):
            return FaunaEncoder.from_datetime(o)
        elif isinstance(o, date):
            return FaunaEncoder.from_date(o)
        elif isinstance(o, (list, tuple)):
            return FaunaEncoder._encode_list(o, _markers)
        elif isinstance(o, dict):
            return FaunaEncoder._encode_dict(o, _markers)
        else:
            raise ValueError(f"Object {o} of type {type(o)} cannot be encoded")

    @staticmethod
    def _encode_list(lst, markers):
        _id = id(lst)
        if _id in markers:
            raise ValueError("Circular reference detected")

        markers.add(id(lst))
        return [FaunaEncoder._encode(elem, markers) for elem in lst]

    @staticmethod
    def _encode_dict(dct, markers):
        _id = id(dct)
        if _id in markers:
            raise ValueError("Circular reference detected")

        markers.add(id(dct))
        if any(i in _RESERVED_TAGS for i in dct.keys()):
            return {
                "@object":
                {k: FaunaEncoder._encode(v, markers)
                 for k, v in dct.items()}
            }
        else:
            return {
                k: FaunaEncoder._encode(v, markers)
                for k, v in dct.items()
            }


class FaunaDecoder:
    """Supports the following types:

     +-------------------+---------------+
     | Python            | Fauna         |
     +===================+===============+
     | dict              | object        |
     +-------------------+---------------+
     | list, tuple       | array         |
     +-------------------+---------------+
     | str               | string        |
     +-------------------+---------------+
     | int               | @int          |
     +-------------------+---------------+
     | int               | @long         |
     +-------------------+---------------+
     | float             | @double       |
     +-------------------+---------------+
     | datetime.datetime | @time         |
     +-------------------+---------------+
     | datetime.date     | @date         |
     +-------------------+---------------+
     | True              | true          |
     +-------------------+---------------+
     | False             | false         |
     +-------------------+---------------+
     | None              | null          |
     +-------------------+---------------+
     | DocumentReference | @doc          |
     +-------------------+---------------+
     | Module            | @mod          |
     +-------------------+---------------+
     """

    @staticmethod
    def decode(obj: Any):
        """Decodes supported objects from the tagged typed into untagged.

        Examples:
            - { "@int": "100" } decodes to 100 of type int
            - { "@double": "100" } decodes to 100.0 of type float
            - { "@long": "100" } decodes to 100 of type int
            - { "@time": "..." } decodes to a datetime
            - { "@date": "..." } decodes to a date
            - { "@doc": "..." } decodes to a DocumentReference
            - { "@mod": "..." } decodes to a Module

        :param obj: the object to decode
        """
        return FaunaDecoder._decode(obj)

    @staticmethod
    def _decode(o: Any, object_tagged: bool = False):
        if isinstance(o, (str, bool, int, float)):
            return o
        elif isinstance(o, list):
            return FaunaDecoder._decode_list(o)
        elif isinstance(o, dict):
            return FaunaDecoder._decode_dict(o, object_tagged)

    @staticmethod
    def _decode_list(lst: List):
        return [FaunaDecoder._decode(i) for i in lst]

    @staticmethod
    def _decode_dict(dct: dict, object_tagged: bool):
        keys = dct.keys()

        # If we're inside an object tag, everything is user-specified
        if object_tagged:
            return {k: FaunaDecoder._decode(v) for k, v in dct.items()}

        if len(keys) == 1:
            if "@int" in keys:
                return int(dct["@int"])
            if "@long" in keys:
                return int(dct["@long"])
            if "@double" in dct:
                return float(dct["@double"])
            if "@object" in dct:
                return FaunaDecoder._decode(dct["@object"], True)
            if "@mod" in dct:
                return Module(dct["@mod"])
            if "@time" in dct:
                return parse_date(dct["@time"])
            if "@date" in dct:
                return parse_date(dct["@date"]).date()
            if "@doc" in dct:
                return DocumentReference.from_string(dct["@doc"])

        return {k: FaunaDecoder._decode(v) for k, v in dct.items()}
