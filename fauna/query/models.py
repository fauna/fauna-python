from collections.abc import Mapping
from datetime import datetime
from typing import Union, Iterator, Any, Optional, List


class Page:
  """A class representing a Set in Fauna."""

  def __init__(self,
               data: Optional[List[Any]] = None,
               after: Optional[str] = None):
    self.data = data
    self.after = after

  def __repr__(self):
    args = []
    if self.data is not None:
      args.append(f"data={repr(self.data)}")

    if self.after is not None:
      args.append(f"after={repr(self.after)}")

    return f"{self.__class__.__name__}({','.join(args)})"

  def __iter__(self) -> Iterator[Any]:
    return iter(self.data or [])

  def __eq__(self, other):
    return isinstance(
        other, Page) and self.data == other.data and self.after == other.after

  def __hash__(self):
    hash((type(self), self.data, self.after))

  def __ne__(self, other):
    return not self.__eq__(other)


class Module:
  """A class representing a Module in Fauna. Examples of modules include Collection, Math, and a user-defined
    collection, among others.

    Usage:

       dogs = Module("Dogs")
       query = fql("${col}.all", col=dogs)
    """

  def __init__(self, name: str):
    self.name = name

  def __repr__(self):
    return f"{self.__class__.__name__}(name={repr(self.name)})"

  def __eq__(self, other):
    return isinstance(other, Module) and str(self) == str(other)

  def __hash__(self):
    hash(self.name)


class BaseReference:
  _collection: Module

  @property
  def coll(self) -> Module:
    return self._collection

  def __init__(self, coll: Union[str, Module]):
    if isinstance(coll, Module):
      self._collection = coll
    elif isinstance(coll, str):
      self._collection = Module(coll)
    else:
      raise TypeError(
          f"'coll' should be of type Module or str, but was {type(coll)}")

  def __repr__(self):
    return f"{self.__class__.__name__}(coll={repr(self._collection)})"

  def __eq__(self, other):
    return isinstance(other, type(self)) and str(self) == str(other)


class DocumentReference(BaseReference):
  """A class representing a reference to a :class:`Document` stored in Fauna.
    """

  @property
  def id(self) -> str:
    """The ID for the :class:`Document`. Valid IDs are 64-bit integers, stored as strings.

        :rtype: str
        """
    return self._id

  def __init__(self, coll: Union[str, Module], id: str):
    super().__init__(coll)

    if not isinstance(id, str):
      raise TypeError(f"'id' should be of type str, but was {type(id)}")
    self._id = id

  def __hash__(self):
    hash((type(self), self._collection, self._id))

  def __repr__(self):
    return f"{self.__class__.__name__}(id={repr(self._id)},coll={repr(self._collection)})"

  @staticmethod
  def from_string(ref: str):
    rs = ref.split(":")
    if len(rs) != 2:
      raise ValueError("Expects string of format <CollectionName>:<ID>")
    return DocumentReference(rs[0], rs[1])


class NamedDocumentReference(BaseReference):
  """A class representing a reference to a :class:`NamedDocument` stored in Fauna.
    """

  @property
  def name(self) -> str:
    """The name of the :class:`NamedDocument`.

        :rtype: str
        """
    return self._name

  def __init__(self, coll: Union[str, Module], name: str):
    super().__init__(coll)

    if not isinstance(name, str):
      raise TypeError(f"'name' should be of type str, but was {type(name)}")

    self._name = name

  def __hash__(self):
    hash((type(self), self._collection, self._name))

  def __repr__(self):
    return f"{self.__class__.__name__}(name={repr(self._name)},coll={repr(self._collection)})"


class NullDocument:

  @property
  def cause(self) -> Optional[str]:
    return self._cause

  @property
  def ref(self) -> Union[DocumentReference, NamedDocumentReference]:
    return self._ref

  def __init__(
      self,
      ref: Union[DocumentReference, NamedDocumentReference],
      cause: Optional[str] = None,
  ):
    self._cause = cause
    self._ref = ref

  def __repr__(self):
    return f"{self.__class__.__name__}(ref={repr(self.ref)},cause={repr(self._cause)})"

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return False

    return self.ref == other.ref and self.cause == other.cause

  def __ne__(self, other):
    return not self == other


class BaseDocument(Mapping):
  """A base document class implementing an immutable mapping.
    """

  def __init__(self, *args, **kwargs):
    self._store = dict(*args, **kwargs)

  def __getitem__(self, __k: str) -> Any:
    return self._store[__k]

  def __len__(self) -> int:
    return len(self._store)

  def __iter__(self) -> Iterator[Any]:
    return iter(self._store)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return False

    if len(self) != len(other):
      return False

    for k, v in self.items():
      if k not in other:
        return False
      if self[k] != other[k]:
        return False

    return True

  def __ne__(self, other):
    return not self.__eq__(other)


class Document(BaseDocument):
  """A class representing a user document stored in Fauna.

    User data should be stored directly on the map, while id, ts, and coll should only be stored on the related
    properties. When working with a :class:`Document` in code, it should be considered immutable.
    """

  @property
  def id(self) -> str:
    return self._id

  @property
  def ts(self) -> datetime:
    return self._ts

  @property
  def coll(self) -> Module:
    return self._coll

  def __init__(self,
               id: str,
               ts: datetime,
               coll: Union[str, Module],
               data: Optional[Mapping] = None):
    if not isinstance(id, str):
      raise TypeError(f"'id' should be of type str, but was {type(id)}")

    if not isinstance(ts, datetime):
      raise TypeError(f"'ts' should be of type datetime, but was {type(ts)}")

    if not (isinstance(coll, str) or isinstance(coll, Module)):
      raise TypeError(
          f"'coll' should be of type Module or str, but was {type(coll)}")

    if isinstance(coll, str):
      coll = Module(coll)

    self._id = id
    self._ts = ts
    self._coll = coll

    super().__init__(data or {})

  def __eq__(self, other):
    return type(self) == type(other) \
        and self.id == other.id \
        and self.coll == other.coll \
        and self.ts == other.ts \
        and super().__eq__(other)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    kvs = ",".join([f"{repr(k)}:{repr(v)}" for k, v in self.items()])

    return f"{self.__class__.__name__}(" \
           f"id={repr(self.id)}," \
           f"coll={repr(self.coll)}," \
           f"ts={repr(self.ts)}," \
           f"data={{{kvs}}})"


class NamedDocument(BaseDocument):
  """A class representing a named document stored in Fauna. Examples of named documents include Collection
    definitions, Index definitions, and Roles, among others.

    When working with a :class:`NamedDocument` in code, it should be considered immutable.
    """

  @property
  def name(self) -> str:
    return self._name

  @property
  def ts(self) -> datetime:
    return self._ts

  @property
  def coll(self) -> Module:
    return self._coll

  def __init__(self,
               name: str,
               ts: datetime,
               coll: Union[Module, str],
               data: Optional[Mapping] = None):
    if not isinstance(name, str):
      raise TypeError(f"'name' should be of type str, but was {type(name)}")

    if not isinstance(ts, datetime):
      raise TypeError(f"'ts' should be of type datetime, but was {type(ts)}")

    if not (isinstance(coll, str) or isinstance(coll, Module)):
      raise TypeError(
          f"'coll' should be of type Module or str, but was {type(coll)}")

    if isinstance(coll, str):
      coll = Module(coll)

    self._name = name
    self._ts = ts
    self._coll = coll

    super().__init__(data or {})

  def __eq__(self, other):
    return type(self) == type(other) \
        and self.name == other.name \
        and self.coll == other.coll \
        and self.ts == other.ts \
        and super().__eq__(other)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    kvs = ",".join([f"{repr(k)}:{repr(v)}" for k, v in self.items()])

    return f"{self.__class__.__name__}(" \
           f"name={repr(self.name)}," \
           f"coll={repr(self.coll)}," \
           f"ts={repr(self.ts)}," \
           f"data={{{kvs}}})"
