import abc
from typing import Any, Sequence, Mapping, Optional, List

from fauna.template import FaunaTemplate


class QueryBuilder(abc.ABC):
    """An abstract class for query builders that build to the FQL Query Template wire protocol.
    """

    @abc.abstractmethod
    def fragments(self) -> Sequence['Fragment']:
        """An abstract method for converting a builder to query template wire protocol.
        e.g. ``{ "fql": [ ... ] }``

        :returns: a rendered query template
        """
        pass


class Fragment(abc.ABC):
    """An abstract class representing a Fragment of a query.
    """

    @abc.abstractmethod
    def get(self) -> Any:
        """An abstract method for rendering the :class:`Fragment` into a query part.
        """
        pass


class ValueFragment(Fragment):
    """A concrete :class:`Fragment` representing a part of a query that will become a type tagged object on the wire.
    For example, if a template contains a variable ``${foo}``, and an object ``{ "prop": 1 }`` is provided for foo,
    then ``{ "prop": 1 }`` should be wrapped as a :class:`ValueFragment`.

    :param Any val: The value to be used as a fragment.
    """

    def __init__(self, val: Any):
        self._val = val

    def get(self) -> Any:
        """Gets the stored value.

        :returns: The stored value.
        """
        return self._val


class LiteralFragment(Fragment):
    """A concrete :class:`Fragment` representing a query literal For example, in the template ```let x = ${foo}```,
    the portion ```let x = ``` is a query literal and should be wrapped as a :class:`LiteralFragment`.

    :param str val: The query literal to be used as a fragment.
    """

    def __init__(self, val: str):
        self._val = val

    def get(self) -> str:
        """Renders the :class:`LiteralFragment` into the wire protocol for a literal of the query template API.

        e.g. ``let x = ``

        :returns: The query literal.
        """
        return self._val


class QueryInterpolationBuilder(QueryBuilder):
    """A concrete :class:`QueryBuilder` for building queries into the query template wire protocol.
    """
    _rendered: Optional[Mapping[str, Any]]
    _fragments: List[Fragment]

    def __init__(self, fragments: Optional[List[Fragment]] = None):
        self._rendered = None
        self._fragments = fragments or []

    @property
    def fragments(self) -> List[Fragment]:
        """The list of stored Fragments"""
        return self._fragments


def fql(query: str, **kwargs: Any) -> QueryBuilder:
    """Creates a QueryBuilder - capable of performing query composition and simple querying. It can accept a simple
    string query, or can perform composition using ${}-sigil string template with ``**kwargs`` as substitutions.

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
            return fql('Dogs.byId(${id})', id=id)

        def get_vet_phone(id):
            return fql('${dog} { .vet_phone_number }', dog=get_dog(id))

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
            fragments.append(ValueFragment(kwargs[field_name]))
    return QueryInterpolationBuilder(fragments)
