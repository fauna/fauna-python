from typing import Optional, Tuple, Iterator, Match
import re as _re


class FaunaTemplate:
  """A template class that supports variables marked with a ${}-sigil. Its primary purpose
    is to expose an iterator for the template parts that support composition of FQL queries.

    Implementation adapted from https://github.com/python/cpython/blob/main/Lib/string.py

    :param template: A string template e.g. "${my_var} { name }"
    :type template: str
    """

  _delimiter = '$'
  _idpattern = r'[_a-zA-Z][_a-zA-Z0-9]*'
  _flags = _re.VERBOSE

  def __init__(self, template: str):
    """The initializer"""
    delim = _re.escape(self._delimiter)
    pattern = fr"""
        {delim}(?:
          (?P<escaped>{delim})  |   # Escape sequence of two delimiters
          {{(?P<braced>{self._idpattern})}} |   # delimiter and a braced identifier
          (?P<invalid>)             # Other ill-formed delimiter exprs
        ) 
        """
    self._pattern = _re.compile(pattern, self._flags)
    self._template = template

  def iter(self) -> Iterator[Tuple[Optional[str], Optional[str]]]:
    """A method that returns an iterator over tuples representing template parts. The
        first value of the tuple, if not None, is a template literal. The second value of
        the tuple, if not None, is a template variable. If both are not None, then the
        template literal comes *before* the variable.

        :raises ValueError: If there is an invalid template placeholder

        :return: An iterator of template parts
        :rtype: collections.Iterable[Tuple[Optional[str], Optional[str]]]
        """
    match_objects = self._pattern.finditer(self._template)
    cur_pos = 0
    for mo in match_objects:
      if mo.group("invalid") is not None:
        self._handle_invalid(mo)

      span_start_pos = mo.span()[0]
      span_end_pos = mo.span()[1]
      escaped_part = mo.group("escaped") or ""
      variable_part = mo.group("braced")
      literal_part: Optional[str] = None

      if cur_pos != span_start_pos:
        literal_part = \
            self._template[cur_pos:span_start_pos] \
                + escaped_part

      cur_pos = span_end_pos

      yield literal_part, variable_part

    if cur_pos != len(self._template):
      yield self._template[cur_pos:], None

  def _handle_invalid(self, mo: Match) -> None:
    i = mo.start("invalid")
    lines = self._template[:i].splitlines(keepends=True)

    if not lines:
      colno = 1
      lineno = 1
    else:
      colno = i - len(''.join(lines[:-1]))
      lineno = len(lines)

    raise ValueError(
        f"Invalid placeholder in template: line {lineno}, col {colno}")
