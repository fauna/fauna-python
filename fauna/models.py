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


class DocumentReference:
    collection: Module
    ref_id: str

    def __init__(self, collection: Union[str, Module], ref_id: str):
        if isinstance(collection, str):
            self.collection = Module(collection)
        else:
            self.collection = collection

        self.ref_id = ref_id

    def __str__(self):
        return f"{self.collection}:{self.ref_id}"

    def __eq__(self, other):
        return isinstance(other, DocumentReference) and str(self) == str(other)

    def __hash__(self):
        hash((self.collection, self.ref_id))

    @staticmethod
    def from_string(ref: str):
        rs = ref.split(":")
        if len(rs) != 2:
            raise ValueError(
                "Expects string of format <CollectionName>:<RefID>")
        return DocumentReference(rs[0], rs[1])


class DocumentDict(dict):

    def ref(self) -> DocumentReference:
        for k in ["coll", "id"]:
            if k not in self:
                raise ValueError(
                    f"Document does not contain the required '{k}' key to return a reference"
                )

        return DocumentReference(self["coll"], self["id"])
