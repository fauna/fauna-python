from __future__ import annotations

import abc
import string
from typing import Any, Sequence, Mapping, Optional, List

from fauna.encode import encode_to_typed
from fauna.template import FaunaTemplate


class QueryBuilder(abc.ABC):

    @abc.abstractmethod
    def to_query(self) -> Mapping[str, Sequence[Any]]:
        pass


class Fragment(abc.ABC):

    @abc.abstractmethod
    def render(self) -> Any:
        pass


class ValueFragment(Fragment):

    def __init__(self, val: Any):
        self._val = val

    def render(self):
        encoded = encode_to_typed(self._val)
        return {"value": encoded}


class LiteralFragment(Fragment):

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

    def __init__(self, fragments: Optional[List[Fragment]] = None):
        self._fragments = fragments or []

    def append(self, fragment: Fragment):
        self._fragments.append(fragment)

    def to_query(self) -> Mapping[str, Sequence[Any]]:
        rendered = []
        for f in self._fragments:
            rendered.append(f.render())
        return {"fql": rendered}


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
    template = FaunaTemplate(q)
    for text, field_name in template.expand():
        if text is not None and len(text) > 0:
            fragments.append(LiteralFragment(text))

        if field_name is not None:
            if field_name not in kwargs:
                raise ValueError(
                    f"template variable `{field_name}` not found in provided kwargs"
                )

            # TODO: Reject if it's already a fragment, or accept *Fragment? Decide on API here
            cur_arg = kwargs[field_name]
            if isinstance(cur_arg, FQLTemplateQueryBuilder):
                fragments.append(QueryFragment(cur_arg))
            else:
                fragments.append(ValueFragment(cur_arg))
    return FQLTemplateQueryBuilder(fragments)
