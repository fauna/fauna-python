from __future__ import annotations

import abc
import string
from typing import Any, Sequence, Mapping, Optional, List

from fauna.encode import encode_to_typed


class QueryBuilder(abc.ABC):

    @abc.abstractmethod
    def to_query(self) -> Mapping[str, Sequence[any]]:
        pass


class Fragment(abc.ABC):

    @abc.abstractmethod
    def render(self) -> any:
        pass


class ValueFragment(Fragment):

    def __init__(self, val: str):
        self._val = val

    def render(self):
        return self._val


class StringFragment(Fragment):

    def __init__(self, val: str):
        self._val = val

    def render(self):
        return self._val


class QueryFragment(Fragment):

    def __init__(self, builder: QueryBuilder):
        self._builder = builder

    def render(self):
        return self._builder.to_query()


class FQLTemplateQueryBuilder(QueryBuilder):
    _fragments: List[Fragment]

    def __init__(self, fragments: Optional[Sequence[Fragment]] = None):
        if fragments is None:
            fragments = []
        self._fragments = fragments

    def append(self, fragment: Fragment):
        self._fragments.append(fragment)

    def to_query(self) -> Mapping[str, Sequence[any]]:
        rendered = []
        for f in self._fragments:
            if isinstance(f, ValueFragment):
                encoded = encode_to_typed(f.render())
                rendered.append({"value": encoded})
            else:
                rendered.append(f.render())
        return {"fql": rendered}

    @staticmethod
    def from_fragments(fragments) -> QueryBuilder:
        qb = FQLTemplateQueryBuilder(fragments)
        return qb


def fql(q: str, **kwargs: Any) -> QueryBuilder:
    """
    let y = {{ why: {why}, what: {what} }}
    y {{ .why }}

    becomes...

    literal_text:let y = {, field_name:None, format_spec:None, conversion:None
    literal_text: why: , field_name:why, format_spec:, conversion:None
    literal_text:, what: , field_name:what, format_spec:, conversion:None
    literal_text: }, field_name:None, format_spec:None, conversion:None
    literal_text:\ny {, field_name:None, format_spec:None, conversion:None
    literal_text: .why }, field_name:None, format_spec:None, conversion:None
    """
    fragments = []

    for text, field_name, _, _ in string.Formatter().parse(q):
        if text is not None and len(text) > 0:
            fragments.append(StringFragment(text))

        if field_name is not None:
            if field_name not in kwargs:
                raise ValueError(
                    "template variable not found in provided kwargs")

            cur_arg = kwargs[field_name]
            if isinstance(cur_arg, FQLTemplateQueryBuilder):
                fragments.append(QueryFragment(cur_arg))
            else:
                fragments.append(ValueFragment(cur_arg))
    return FQLTemplateQueryBuilder.from_fragments(fragments)
