from typing import Any, List, Union

from iso8601 import parse_date

from fauna.query.models import Module, DocumentReference, Document, NamedDocument, NamedDocumentReference, Page, \
    NullDocument


class FaunaDecoder:
  """Supports the following types:

     +--------------------+---------------+
     | Python             | Fauna         |
     +====================+===============+
     | dict               | object        |
     +--------------------+---------------+
     | list, tuple        | array         |
     +--------------------+---------------+
     | str                | string        |
     +--------------------+---------------+
     | int                | @int          |
     +--------------------+---------------+
     | int                | @long         |
     +--------------------+---------------+
     | float              | @double       |
     +--------------------+---------------+
     | datetime.datetime  | @time         |
     +--------------------+---------------+
     | datetime.date      | @date         |
     +--------------------+---------------+
     | True               | true          |
     +--------------------+---------------+
     | False              | false         |
     +--------------------+---------------+
     | None               | null          |
     +--------------------+---------------+
     | *DocumentReference | @ref          |
     +--------------------+---------------+
     | *Document          | @doc          |
     +--------------------+---------------+
     | Module             | @mod          |
     +--------------------+---------------+
     | Page               | @set          |
     +--------------------+---------------+

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
            - { "@doc": ... } decodes to a Document or NamedDocument
            - { "@ref": ... } decodes to a DocumentReference or NamedDocumentReference
            - { "@mod": ... } decodes to a Module
            - { "@set": ... } decodes to a Page

        :param obj: the object to decode
        """
    return FaunaDecoder._decode(obj)

  @staticmethod
  def _decode(o: Any, escaped: bool = False):
    if isinstance(o, (str, bool, int, float)):
      return o
    elif isinstance(o, list):
      return FaunaDecoder._decode_list(o)
    elif isinstance(o, dict):
      return FaunaDecoder._decode_dict(o, escaped)

  @staticmethod
  def _decode_list(lst: List):
    return [FaunaDecoder._decode(i) for i in lst]

  @staticmethod
  def _decode_dict(dct: dict, escaped: bool):
    keys = dct.keys()

    # If escaped, everything is user-specified
    if escaped:
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
        value = dct["@doc"]
        if isinstance(value, str):
          # Not distinguishing between DocumentReference and NamedDocumentReference because this shouldn't
          # be an issue much longer
          return DocumentReference.from_string(value)

        contents = FaunaDecoder._decode(value)

        if "id" in contents and "coll" in contents and "ts" in contents:
          doc_id = contents.pop("id")
          doc_coll = contents.pop("coll")
          doc_ts = contents.pop("ts")

          return Document(
              id=doc_id,
              coll=doc_coll,
              ts=doc_ts,
              data=contents,
          )
        elif "name" in contents and "coll" in contents and "ts" in contents:
          doc_name = contents.pop("name")
          doc_coll = contents.pop("coll")
          doc_ts = contents.pop("ts")

          return NamedDocument(
              name=doc_name,
              coll=doc_coll,
              ts=doc_ts,
              data=contents,
          )
        else:
          # Unsupported document reference. Return the unwrapped value to futureproof.
          return contents

      if "@ref" in dct:
        value = dct["@ref"]
        if "id" not in value and "name" not in value:
          # Unsupported document reference. Return the unwrapped value to futureproof.
          return value

        col = FaunaDecoder._decode(value["coll"])
        doc_ref: Union[DocumentReference, NamedDocumentReference]

        if "id" in value:
          doc_ref = DocumentReference(col, value["id"])
        else:
          doc_ref = NamedDocumentReference(col, value["name"])

        if "exists" in value and not value["exists"]:
          cause = value["cause"] if "cause" in value else None
          return NullDocument(doc_ref, cause)

        return doc_ref

      if "@set" in dct:
        value = dct["@set"]
        if isinstance(value, str):
          return Page(after=value)

        after = value["after"] if "after" in value else None
        data = FaunaDecoder._decode(value["data"]) if "data" in value else None

        return Page(data=data, after=after)

    return {k: FaunaDecoder._decode(v) for k, v in dct.items()}
