from datetime import datetime, date
from typing import Any, Optional, Set

from fauna.query.models import DocumentReference, Module, Document, NamedDocument, NamedDocumentReference, NullDocument
from fauna.query.query_builder import Query, Fragment, LiteralFragment, ValueFragment

_RESERVED_TAGS = [
    "@date",
    "@doc",
    "@double",
    "@int",
    "@long",
    "@mod",
    "@object",
    "@ref",
    "@set",
    "@time",
]


class FaunaEncoder:
  """Supports the following types:

    +-------------------------------+---------------+
    | Python                        | Fauna Tags    |
    +===============================+===============+
    | dict                          | object        |
    +-------------------------------+---------------+
    | list, tuple                   | array         |
    +-------------------------------+---------------+
    | str                           | value, N/A    |
    +-------------------------------+---------------+
    | int 32-bit signed             | value, @int   |
    +-------------------------------+---------------+
    | int 64-bit signed             | value, @long  |
    +-------------------------------+---------------+
    | float                         | value, @double|
    +-------------------------------+---------------+
    | datetime.datetime             | value, @time  |
    +-------------------------------+---------------+
    | datetime.date                 | value, @date  |
    +-------------------------------+---------------+
    | True                          | value, N/A    |
    +-------------------------------+---------------+
    | False                         | value, N/A    |
    +-------------------------------+---------------+
    | None                          | value, N/A    |
    +-------------------------------+---------------+
    | *Document                     | value, @ref   |
    +-------------------------------+---------------+
    | *DocumentReference            | @ref          |
    +-------------------------------+---------------+
    | Module                        | @mod          |
    +-------------------------------+---------------+
    | Query                         | fql           |
    +-------------------------------+---------------+

    """

  @staticmethod
  def encode(obj: Any) -> Any:
    """Encodes supported objects into the wire protocol.

        Examples:
            - Up to 32-bit ints encode to {"value": { "@int": "..." }}
            - Up to 64-bit ints encode to {"value": { "@long": "..." }}
            - Floats encode to {"value": { "@double": "..." }}
            - datetime encodes to {"value": { "@time": "..." }}
            - date encodes to {"value": { "@date": "..." }}
            - Objects encode to {"object": { ... }}, and its values are recursively encoded
            - Lists and Tuples encode to {"array": [...]}, and its values are recursively encoded
            - Query encodes to { "fql": [...] }

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
      raise ValueError("Precision loss when converting int to Fauna type")

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
    if obj.utcoffset() is None:
      raise ValueError("datetimes must be timezone-aware")

    return {"@time": obj.isoformat(sep="T")}

  @staticmethod
  def from_date(obj: date):
    return {"@date": obj.isoformat()}

  @staticmethod
  def from_doc_ref(obj: DocumentReference):
    return {"@ref": {"id": obj.id, "coll": FaunaEncoder.from_mod(obj.coll)}}

  @staticmethod
  def from_named_doc_ref(obj: NamedDocumentReference):
    return {"@ref": {"name": obj.name, "coll": FaunaEncoder.from_mod(obj.coll)}}

  @staticmethod
  def from_mod(obj: Module):
    return {"@mod": obj.name}

  @staticmethod
  def from_none():
    return None

  @staticmethod
  def from_fragment(obj: Fragment):
    if isinstance(obj, LiteralFragment):
      return obj.get()
    elif isinstance(obj, ValueFragment):
      return FaunaEncoder.encode(obj.get())
    else:
      raise ValueError(f"Unknown fragment type: {type(obj)}")

  @staticmethod
  def from_query_interpolation_builder(obj: Query):
    return {"fql": [FaunaEncoder.from_fragment(f) for f in obj.fragments]}

  @staticmethod
  def _encode(o: Any, _markers: Optional[Set] = None):
    if _markers is None:
      _markers = set()

    if isinstance(o, str):
      return {"value": FaunaEncoder.from_str(o)}
    elif o is None:
      return {"value": FaunaEncoder.from_none()}
    elif o is True:
      return {"value": FaunaEncoder.from_bool(o)}
    elif o is False:
      return {"value": FaunaEncoder.from_bool(o)}
    elif isinstance(o, int):
      return {"value": FaunaEncoder.from_int(o)}
    elif isinstance(o, float):
      return {"value": FaunaEncoder.from_float(o)}
    elif isinstance(o, Module):
      return {"value": FaunaEncoder.from_mod(o)}
    elif isinstance(o, DocumentReference):
      return {"value": FaunaEncoder.from_doc_ref(o)}
    elif isinstance(o, NamedDocumentReference):
      return {"value": FaunaEncoder.from_named_doc_ref(o)}
    elif isinstance(o, datetime):
      return {"value": FaunaEncoder.from_datetime(o)}
    elif isinstance(o, date):
      return {"value": FaunaEncoder.from_date(o)}
    elif isinstance(o, Document):
      return {"value": FaunaEncoder.from_doc_ref(DocumentReference(o.coll, o.id))}
    elif isinstance(o, NamedDocument):
      return {"value": FaunaEncoder.from_named_doc_ref(
          NamedDocumentReference(o.coll, o.name))}
    elif isinstance(o, NullDocument):
      return FaunaEncoder.encode(o.ref)
    elif isinstance(o, (list, tuple)):
      return FaunaEncoder._encode_list(o, _markers)
    elif isinstance(o, dict):
      return FaunaEncoder._encode_dict(o, _markers)
    elif isinstance(o, Query):
      return FaunaEncoder.from_query_interpolation_builder(o)
    else:
      raise ValueError(f"Object {o} of type {type(o)} cannot be encoded")

  @staticmethod
  def _encode_list(lst, markers):
    _id = id(lst)
    if _id in markers:
      raise ValueError("Circular reference detected")

    markers.add(id(lst))
    return {"array": [FaunaEncoder._encode(elem, markers) for elem in lst]}

  @staticmethod
  def _encode_dict(dct, markers):
    _id = id(dct)
    if _id in markers:
      raise ValueError("Circular reference detected")

    markers.add(id(dct))
    return {"object": {k: FaunaEncoder._encode(v, markers) for k, v in dct.items()}}
