class DocumentReference:

    def __init__(self, collection_name: str, ref_id: str):
        self.collection = collection_name
        self.id = ref_id

    def __str__(self):
        return f"{self.collection}:{self.id}"

    def __eq__(self, other):
        return isinstance(other, DocumentReference) and str(self) == str(other)

    def __hash__(self):
        hash((self.collection, self.id))

    @staticmethod
    def from_string(ref: str):
        rs = ref.split(":")
        if len(rs) != 2:
            raise ValueError(
                "Expects string of format <CollectionName>:<RefID>")
        return DocumentReference(rs[0], rs[1])


class Module:

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Module) and str(self) == str(other)

    def __hash__(self):
        hash(self.name)
