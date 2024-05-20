import base64
from datetime import datetime, date
from typing import Any, Optional, List, Union

from fauna.query.models import DocumentReference, Module, Document, NamedDocument, NamedDocumentReference, NullDocument, \
  StreamToken
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
    | dict                          | @object       |
    +-------------------------------+---------------+
    | list, tuple                   | array         |
    +-------------------------------+---------------+
    | str                           | string        |
    +-------------------------------+---------------+
    | int 32-bit signed             | @int          |
    +-------------------------------+---------------+
    | int 64-bit signed             | @long         |
    +-------------------------------+---------------+
    | float                         | @double       |
    +-------------------------------+---------------+
    | datetime.datetime             | @time         |
    +-------------------------------+---------------+
    | datetime.date                 | @date         |
    +-------------------------------+---------------+
    | True                          | True          |
    +-------------------------------+---------------+
    | False                         | False         |
    +-------------------------------+---------------+
    | None                          | None          |
    +-------------------------------+---------------+
    | bytes / bytearray             | @bytes        |
    +-------------------------------+---------------+
    | *Document                     | @ref          |
    +-------------------------------+---------------+
    | *DocumentReference            | @ref          |
    +-------------------------------+---------------+
    | Module                        | @mod          |
    +-------------------------------+---------------+
    | Query                         | fql           |
    +-------------------------------+---------------+
    | ValueFragment                 | value         |
    +-------------------------------+---------------+
    | TemplateFragment              | string        |
    +-------------------------------+---------------+
    | StreamToken                   | string        |
    +-------------------------------+---------------+

    """

  @staticmethod
  def encode(obj: Any) -> Any:
    """Encodes supported objects into the tagged format.

        Examples:
            - Up to 32-bit ints encode to { "@int": "..." }
            - Up to 64-bit ints encode to { "@long": "..." }
            - Floats encode to { "@double": "..." }
            - datetime encodes to { "@time": "..." }
            - date encodes to { "@date": "..." }
            - DocumentReference encodes to { "@doc": "..." }
            - Module encodes to { "@mod": "..." }
            - Query encodes to { "fql": [...] }
            - ValueFragment encodes to { "value": <encoded_val> }
            - LiteralFragment encodes to a string
            - StreamToken encodes to a string

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
  def from_bytes(obj: Union[bytearray, bytes]):
    return {"@bytes": base64.b64encode(obj).decode('ascii')}

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
  def from_dict(obj: Any):
    return {"@object": obj}

  @staticmethod
  def from_none():
    return None

  @staticmethod
  def from_fragment(obj: Fragment):
    if isinstance(obj, LiteralFragment):
      return obj.get()
    elif isinstance(obj, ValueFragment):
      v = obj.get()
      if isinstance(v, Query):
        return FaunaEncoder.from_query_interpolation_builder(v)
      else:
        return {"value": FaunaEncoder.encode(v)}
    else:
      raise ValueError(f"Unknown fragment type: {type(obj)}")

  @staticmethod
  def from_query_interpolation_builder(obj: Query):
    return {"fql": [FaunaEncoder.from_fragment(f) for f in obj.fragments]}

  @staticmethod
  def from_streamtoken(obj: StreamToken):
    return {"@stream": obj.token}

  @staticmethod
  def _encode(o: Any, _markers: Optional[List] = None):
    if _markers is None:
      _markers = []

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
    elif isinstance(o, NamedDocumentReference):
      return FaunaEncoder.from_named_doc_ref(o)
    elif isinstance(o, datetime):
      return FaunaEncoder.from_datetime(o)
    elif isinstance(o, date):
      return FaunaEncoder.from_date(o)
    elif isinstance(o, bytearray) or isinstance(o, bytes):
      return FaunaEncoder.from_bytes(o)
    elif isinstance(o, Document):
      return FaunaEncoder.from_doc_ref(DocumentReference(o.coll, o.id))
    elif isinstance(o, NamedDocument):
      return FaunaEncoder.from_named_doc_ref(
          NamedDocumentReference(o.coll, o.name))
    elif isinstance(o, NullDocument):
      return FaunaEncoder.encode(o.ref)
    elif isinstance(o, (list, tuple)):
      return FaunaEncoder._encode_list(o, _markers)
    elif isinstance(o, dict):
      return FaunaEncoder._encode_dict(o, _markers)
    elif isinstance(o, Query):
      return FaunaEncoder.from_query_interpolation_builder(o)
    elif isinstance(o, StreamToken):
      return FaunaEncoder.from_streamtoken(o)
    else:
      raise ValueError(f"Object {o} of type {type(o)} cannot be encoded")

  @staticmethod
  def _encode_list(lst, markers):
    _id = id(lst)
    if _id in markers:
      raise ValueError("Circular reference detected")

    markers.append(id(lst))
    res = [FaunaEncoder._encode(elem, markers) for elem in lst]
    markers.pop()
    return res

  @staticmethod
  def _encode_dict(dct, markers):
    _id = id(dct)
    if _id in markers:
      raise ValueError("Circular reference detected")

    markers.append(id(dct))
    if any(i in _RESERVED_TAGS for i in dct.keys()):
      res = {
          "@object": {
              k: FaunaEncoder._encode(v, markers) for k, v in dct.items()
          }
      }
      markers.pop()
      return res
    else:
      res = {k: FaunaEncoder._encode(v, markers) for k, v in dct.items()}
      markers.pop()
      return res
