import abc
from typing import Any, Sequence, Mapping, Optional, List

from fauna.template import FaunaTemplate
from fauna.wire_protocol import FaunaEncoder


class QueryBuilder(abc.ABC):
    """An abstract class for query builders that build to the FQL Query Template wire protocol.
    """

    @abc.abstractmethod
    def to_query(self, encoder: FaunaEncoder) -> Mapping[str, Sequence[Any]]:
        """An abstract method for converting a builder to query template wire protocol.
        e.g. ``{ "fql": [ ... ] }``

        :returns: a rendered query template
        """
        pass


class Fragment(abc.ABC):
    """An abstract class representing a Fragment of a query.
    """

    @abc.abstractmethod
    def render(self, encoder: FaunaEncoder) -> Any:
        """An abstract method for rendering the :class:`Fragment` into a query part.
        """
        pass


class ValueFragment(Fragment):
    """A concrete :class:`Fragment` representing a part of a query that will become a type tagged object on the wire.
    For example, if a template contains a variable ``$foo``, and an object ``{ "prop": 1 }`` is provided for foo,
    then ``{ "prop": 1 }`` should be wrapped as a :class:`ValueFragment`.

    :param Any val: The value, which must be serializable to tagged format, to be used as a fragment.
    """

    def __init__(self, val: Any):
        self._val = val

    def render(self, encoder) -> Mapping[str, Any]:
        """Renders the :class:`ValueFragment` into the wire protocol for a value of the query template API.

        e.g. ``{ "value": <encoded_value> }``

        :returns: The value fragment encoded to the wire protocol.
        :raises ValueError: If encoding to tagged format fails.
        """
        encoded = encoder.encode(self._val)
        return {"value": encoded}


class LiteralFragment(Fragment):
    """A concrete :class:`Fragment` representing a query literal For example, in the template ```let x = $foo```,
    the portion ```let x = ``` is a query literal and should be wrapped as a :class:`LiteralFragment`.

    :param str val: The query literal to be used as a fragment.
    """

    def __init__(self, val: str):
        self._val = val

    def render(self, _) -> str:
        """Renders the :class:`LiteralFragment` into the wire protocol for a literal of the query template API.

        e.g. ``let x = ``

        :returns: The query literal.
        """
        return self._val


class QueryFragment(Fragment):
    """A concrete :class:`Fragment` representing a subquery within a template. For example, if a template contains a
    variable ```$foo_query```, and a :class:`QueryBuilder` is provided for foo, then it should be wrapped as a
    :class:`QueryFragment`.

    :param QueryBuilder builder: A builder that will be used as a query fragment.
    """

    def __init__(self, builder: QueryBuilder):
        self._builder = builder

    def render(self, encoder: FaunaEncoder) -> Mapping[str, Sequence[Any]]:
        """Renders the :class:`QueryFragment` into the wire protocol for a query within the query template API.

        e.g. ``{ "fql": [ ... ] }``

        :returns: The query rendered into the wire protocol.
        """
        return self._builder.to_query(encoder)


class FQLTemplateQueryBuilder(QueryBuilder):
    """A concrete :class:`QueryBuilder` for building queries into the query template wire protocol.
    """

    _fragments: List[Fragment]

    def __init__(self, fragments: Optional[List[Fragment]] = None):
        self._fragments = fragments or []

    def append(self, fragment: Fragment) -> None:
        """Appends a :class:`Fragment` to the end of the builder."""
        self._fragments.append(fragment)

    def to_query(self, encoder: FaunaEncoder) -> Mapping[str, Sequence[Any]]:
        """Converts the builder and all fragments into the query template wire protocol.
        e.g. ``{ "fql": [ ... ] }``

        :returns: A fully rendered query template.
        """
        rendered = []
        for f in self._fragments:
            rendered.append(f.render(encoder))
        return {"fql": rendered}


def fql(query: str, **kwargs: Any) -> QueryBuilder:
    """Creates a QueryBuilder - capable of performing query composition and simple querying. It can accept a simple
    string query, or can perform composition using $-sigil string template with ``**kwargs`` as substitutions.

    The ``**kwargs`` can be Fauna data types - such as strings, document references, or modules - and embedded
    QueryBuilders - allowing you to compose arbitrarily complex queries.

    When providing ``**kwargs``, following types are accepted:
        - :class:`str`, :class:`int`, :class:`float`, :class:`bool`, :class:`datetime.datetime`, :class:`datetime.date`,
          :class:`dict`, :class:`list`, :class:`QueryBuilder`, :class:`DocumentReference`, :class:`Module`

    :raises ValueError: If there is an invalid template placeholder or a value that cannot be encoded.
    :returns: A :class:`QueryBuilder` that can be passed to the client for evaluation against Fauna.

    Examples:

    .. code-block:: python
        :name: Simple-FQL-Example
        :caption: Simple query declaration using this function.

        fql('Dogs.byName("Fido")')

    .. code-block:: python
        :name: Composition-FQL-Example
        :caption: Query composition using this function.

        def get_dog(id):
            return fql('Dogs.byId($id)', id=id)

        def get_vet_phone(id):
            return fql('$dog { .vet_phone_number }', dog=get_dog(id))

        get_vet_phone('d123')

    """

    fragments: List[Any] = []
    template = FaunaTemplate(query)
    for text, field_name in template.iter():
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
