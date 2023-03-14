from typing import Union


class Module:

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Module) and str(self) == str(other)

    def __hash__(self):
        hash(self.name)


class BaseReference:
    _collection: Module

    def __init__(self, coll: Union[str, Module]):
        if isinstance(coll, Module):
            self._collection = coll
        elif isinstance(coll, str):
            self._collection = Module(coll)
        else:
            raise TypeError(
                f"Coll must be either a Module or a string, but was a {type(coll)}"
            )

    @property
    def coll(self) -> Module:
        return self._collection


class DocumentReference(BaseReference):
    _id: int

    def __init__(self, coll: Union[str, Module], ref_id: int):
        super().__init__(coll)
        self._id = ref_id

    def __hash__(self):
        hash((type(self), self._collection, self._id))

    def __str__(self):
        return f"{self._collection}:{self._id}"

    def __eq__(self, other):
        return isinstance(other, type(self)) and str(self) == str(other)

    @property
    def id(self) -> int:
        return self._id

    @staticmethod
    def from_string(ref: str):
        rs = ref.split(":")
        if len(rs) != 2:
            raise ValueError("Expects string of format <CollectionName>:<ID>")
        return DocumentReference(rs[0], int(rs[1]))


class NamedDocumentReference(BaseReference):
    _name: str

    def __init__(self, coll: Union[str, Module], name: str):
        super().__init__(coll)
        self._name = name

    def __hash__(self):
        hash((type(self), self._collection, self._name))

    def __str__(self):
        return f"{self._collection}:{self._name}"

    def __eq__(self, other):
        return isinstance(other, type(self)) and str(self) == str(other)

    @property
    def name(self) -> str:
        return self._name


class BaseDocument(dict):

    def __hash__(self):
        hash((type(self), super().__hash__()))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)


class Document(BaseDocument):

    def __init__(self, data: dict):
        if "coll" not in data or "id" not in data:
            raise ValueError("Data must contain the 'coll' and 'id' keys")

        super().__init__(data)

    @property
    def ref(self) -> DocumentReference:
        return DocumentReference(self["coll"], self["id"])


class NamedDocument(BaseDocument):

    def __init__(self, data: dict):
        if "coll" not in data or "name" not in data:
            raise ValueError("Data must contain the 'coll' and 'name' keys")

        super().__init__(data)

    @property
    def ref(self) -> NamedDocumentReference:
        return NamedDocumentReference(self["coll"], self["name"])
