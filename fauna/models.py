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
    _id: str

    def __init__(self, coll: Union[str, Module], id_: str):
        if isinstance(coll, str):
            self._collection = Module(coll)
        else:
            self._collection = coll

        self._id = id_

    def __str__(self):
        return f"{self._collection}:{self._id}"

    def __eq__(self, other):
        return isinstance(other, type(self)) and str(self) == str(other)

    def __hash__(self):
        hash((self._collection, self._id))

    @property
    def collection(self) -> Module:
        return self._collection


class DocumentReference(BaseReference):

    def __init__(self, collection: Union[str, Module], ref_id: str):
        super().__init__(collection, ref_id)

    @property
    def id(self) -> str:
        return self._id

    @staticmethod
    def from_string(ref: str):
        rs = ref.split(":")
        if len(rs) != 2:
            raise ValueError("Expects string of format <CollectionName>:<ID>")
        return DocumentReference(rs[0], rs[1])


class NamedDocumentReference(BaseReference):

    def __init__(self, collection: Union[str, Module], name: str):
        super().__init__(collection, name)

    @property
    def name(self) -> str:
        return self._id


class BaseDocument(dict):
    pass


class Document(BaseDocument):

    def __init__(self, data: dict):
        if "coll" not in data and "id" not in data:
            raise ValueError("Data must contain the 'coll' and 'id' keys")

        super().__init__(data)

    def ref(self) -> DocumentReference:
        return DocumentReference(self["coll"], self["id"])


class NamedDocument(BaseDocument):

    def __init__(self, data: dict):
        if "coll" not in data and "name" not in data:
            raise ValueError("Data must contain the 'coll' and 'name' keys")

        super().__init__(data)

    def ref(self) -> NamedDocumentReference:
        return NamedDocumentReference(self["coll"], self["name"])
