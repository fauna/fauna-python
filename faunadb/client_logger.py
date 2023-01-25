from json import loads

from faunadb._json import to_json
from faunadb.client import RequestResult


def logger(logger_func):
    """
    Function that can be the ``observer`` for a :any:`FaunaClient`.
    Will call ``logger_func`` on a string representation of each :any:`RequestResult`.

    Use it like::

    def log(logged):
        print logged
    client = FaunaClient(observer=logger(log), ...)
    client.ping() # Calls `log`

    :param logger_func: Callback taking a string to be logged.
    """
    return lambda request_result: logger_func(
        show_request_result(request_result))


def show_request_result(request_result: RequestResult):
    """Translates a :any:`RequestResult` to a string suitable for logging."""
    rr = request_result
    parts = []
    log = parts.append

    def _indent(s):
        """Adds extra spaces to the beginning of every newline."""
        indent_str = "  "
        return ("\n" + indent_str).join(s.split("\n"))

    log(f"Fauna {rr.method} {rr.path}\n")
    if rr.request_content is not None:
        log("  Request JSON: %s\n" %
            _indent(to_json(rr.request_content, pretty=True)))
    log("  Response headers: %s\n" %
        _indent(to_json(dict(rr.response_headers), pretty=True)))
    log("  Response Raw: %s\n" % _indent(rr.response_raw))
    log("  Response JSON: %s\n" %
        _indent(to_json(rr.response_content, pretty=True)))
    log("  Response (%i): Network latency %ims\n" %
        (rr.status_code, int(rr.time_taken * 1000)))

    return u"".join(parts)


def json_logger(logger_func):
    """
    Log the wire protocol

    Use it like::

    def log(logged):
        print(json.dumps(logged))

    client = FaunaClient(observer=json_logger(log), ...)
    client.ping() # Calls `log`

    :param logger_func: Callback taking a string to be logged.
    """
    return lambda request_result: logger_func(_to_log_json(request_result))


def _to_log_json(request_result: RequestResult):
    """Translates a :any:`RequestResult` to a string suitable for logging."""
    rr = request_result
    parts: list[dict] = []
    log = parts.append

    log({
        "request": {
            "method": rr.method,
            "path": rr.path,
            "json": rr.request_content,
        }
    })

    log({
        "response": {
            "code": rr.status_code,
            "latency": int(rr.time_taken * 1000),
            "headers": dict(rr.response_headers),
            "raw": loads(rr.response_raw),
            "content": rr.response_content,
        }
    })

    result = {}
    for d in parts:
        result.update(d)

    return result
