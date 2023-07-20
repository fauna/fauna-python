import abc
from typing import Any, Optional, List

from .template import FaunaTemplate


class Fragment(abc.ABC):
  """An abstract class representing a Fragment of a query.
    """

  @abc.abstractmethod
  def get(self) -> Any:
    """An abstract method for returning a stored value.
        """
    pass


class ValueFragment(Fragment):
  """A concrete :class:`Fragment` representing a part of a query that can represent a template variable.
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
    """Returns the stored value.

        :returns: The stored value.
        """
    return self._val


class Query:
  """A class for representing a query.

       e.g. { "fql": [...] }
    """
  _fragments: List[Fragment]

  def __init__(self, fragments: Optional[List[Fragment]] = None):
    self._fragments = fragments or []

  @property
  def fragments(self) -> List[Fragment]:
    """The list of stored Fragments"""
    return self._fragments

  def __str__(self) -> str:
    res = ""
    for f in self._fragments:
      res += str(f.get())

    return res


def fql(query: str, **kwargs: Any) -> Query:
  """Creates a Query - capable of performing query composition and simple querying. It can accept a
    simple string query, or can perform composition using ``${}`` sigil string template with ``**kwargs`` as
    substitutions.

    The ``**kwargs`` can be Fauna data types - such as strings, document references, or modules - and embedded
    Query - allowing you to compose arbitrarily complex queries.

    When providing ``**kwargs``, following types are accepted:
        - :class:`str`, :class:`int`, :class:`float`, :class:`bool`, :class:`datetime.datetime`, :class:`datetime.date`,
          :class:`dict`, :class:`list`, :class:`Query`, :class:`DocumentReference`, :class:`Module`

    :raises ValueError: If there is an invalid template placeholder or a value that cannot be encoded.
    :returns: A :class:`Query` that can be passed to the client for evaluation against Fauna.

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
            f"template variable `{field_name}` not found in provided kwargs")

      # TODO: Reject if it's already a fragment, or accept *Fragment? Decide on API here
      fragments.append(ValueFragment(kwargs[field_name]))
  return Query(fragments)
