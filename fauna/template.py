from typing import Optional, List, Tuple, Generator, Iterator
import re as _re


class FaunaTemplate:
    """
    Pattern adapted from https://github.com/python/cpython/blob/main/Lib/string.py#L57
    """
    _delimiter = '$'
    _idpattern = r'[_a-zA-Z][_a-zA-Z0-9]*'
    _flags = _re.VERBOSE

    def __init__(self, template: str):
        delim = _re.escape(self._delimiter)
        pattern = fr"""
        {delim}(?:
          (?P<escaped>{delim})  |   # Escape sequence of two delimiters
          (?P<named>{self._idpattern})       |   # delimiter and a Python identifier
          (?P<invalid>)             # Other ill-formed delimiter exprs
        ) 
        """
        self._pattern = _re.compile(pattern, self._flags)
        self._template = template

    def expand(self) -> Iterator[Tuple[Optional[str], Optional[str]]]:
        match_objects = self._pattern.finditer(self._template)
        cur_pos = 0
        for mo in match_objects:
            span_start_pos = mo.span()[0]
            span_end_pos = mo.span()[1]
            escaped_part = mo.group("escaped") or ""
            variable_part = mo.group("named")
            literal_part: Optional[str] = None

            if cur_pos != span_start_pos:
                literal_part = self._template[
                    cur_pos:span_start_pos] + escaped_part

            cur_pos = span_end_pos

            yield literal_part, variable_part

        if cur_pos != len(self._template):
            yield self._template[cur_pos:], None
