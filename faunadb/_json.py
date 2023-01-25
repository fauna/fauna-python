from base64 import decode, urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from json import JSONEncoder, dumps, loads

from iso8601 import parse_date

from faunadb.errors import UnexpectedError


def parse_json(json_string):
    """
    Parses a JSON string into python values.
    Also parses :any:`Ref`, :any:`SetRef`, :any:`FaunaTime`, and :class:`date`.
    """
    return loads(json_string, object_hook=_parse_json_hook)


def parse_json_or_none(json_string):
    try:
        return parse_json(json_string)
    except ValueError:
        return None


def _parse_json_hook(dct):
    # pylint: disable=too-many-return-statements
    """
    Looks for FaunaDB types in a JSON object and converts to them if possible.
    """
    if "@int" in dct:
        return int(dct["@int"])
    if "@long" in dct:
        return int(dct["@long"])
    if "@double" in dct:
        return float(dct["@double"])
    if "@object" in dct:
        return dct["@object"]
    if "@module" in dct:
        raise NotImplemented("@module not implemented")
    if "@date" in dct:
        return parse_date(dct["@date"]).date()
    if "@time" in dct:
        return parse_date(dct["@time"])
    if "@doc" in dct:
        raise NotImplemented("@doc not implemented")

    return dct


def to_json(dct, pretty=False, sort_keys=False):
    """
    Opposite of parse_json.
    Converts a :any`_Expr` into a request body, calling :any:`to_fauna_json`.
    """
    if pretty:
        return dumps(dct,
                     cls=_FaunaJSONEncoder,
                     sort_keys=True,
                     indent=2,
                     separators=(", ", ": "))
    return dumps(dct,
                 cls=_FaunaJSONEncoder,
                 sort_keys=sort_keys,
                 separators=(",", ":"))


class _FaunaJSONEncoder(JSONEncoder):
    """Converts values to JSON 'tagged' format."""

    int_ranage = [-2**32 + 1, -2**32 - 1]
    long_range = [-2**64 + 1, -2**64 - 1]

    def default(self, obj):
        if isinstance(obj, int) and -2**31 + 1 <= obj <= 2**31 - 1:
            return {"@int": repr(obj)}
        elif isinstance(obj, int) and -2**63 + 1 <= obj <= 2**63 - 1:
            return {"@long": repr(obj)}
        elif isinstance(obj, int):
            raise ValueError(
                "Precision loss when converting int to Fauna tagged format")
        elif isinstance(obj, float):
            return {"@double": repr(obj)}
        elif isinstance(obj, datetime):
            value = obj.isoformat()
            if len(value) == 10:
                return {"@date": value}
            else:
                return {"@time": value}
        elif isinstance(obj, dict):
            if any(i.startswith("@") for i in obj.keys()):
                return {"@object": obj}
            return obj
        else:
            raise UnexpectedError(
                "Unserializable object {} of type {}".format(obj, type(obj)),
                None)


def stream_content_to_json(buffer):
    values = []

    try:
        content = parse_json(buffer)
        values.append({"content": content, "raw": buffer})
        buffer = ''
    except Exception:
        while True:
            pos = buffer.find("\n") + 1
            if (pos <= 0):
                break
            slice = buffer[0:pos].strip()
            if (len(pos) > 0):
                # discards empty slices due to leading \n
                values.append({"content": slice.decode(), "raw": slice})
                buffer = buffer[pos].encode()

    return {"buffer": buffer, "values": values}