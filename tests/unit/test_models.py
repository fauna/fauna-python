import pytest

from fauna import Document, NamedDocument, Module, DocumentReference, NamedDocumentReference


def test_document_required_props(subtests):
    with subtests.test(msg="must contain 'coll'"):
        with pytest.raises(ValueError,
                           match="Data must contain the 'coll' and 'id' keys"):
            Document({"id": 123})

    with subtests.test(msg="must contain 'id'"):
        with pytest.raises(ValueError,
                           match="Data must contain the 'coll' and 'id' keys"):
            Document({"coll": "hi"})


def test_named_document_required_props(subtests):
    with subtests.test(msg="must contain 'coll'"):
        with pytest.raises(
                ValueError,
                match="Data must contain the 'coll' and 'name' keys"):
            NamedDocument({"name": 123})

    with subtests.test(msg="must contain 'id'"):
        with pytest.raises(
                ValueError,
                match="Data must contain the 'coll' and 'name' keys"):
            NamedDocument({"coll": "hi"})


def test_ref_does_not_conflict(subtests):
    with subtests.test(msg="Document does not conflict"):
        d = Document({"id": 123, "coll": Module("Dogs"), "ref": "my_ref"})
        assert d.ref == DocumentReference(Module("Dogs"), 123)
        assert d["ref"] == "my_ref"

    with subtests.test(msg="NamedDocument does not conflict"):
        nd = NamedDocument({
            "name": "Schema",
            "coll": Module("Dogs"),
            "ref": "my_ref"
        })
        assert nd.ref == NamedDocumentReference(Module("Dogs"), "Schema")
        assert nd["ref"] == "my_ref"


def test_document_equality(subtests):
    with subtests.test(msg="Document does not equal NamedDocument"):
        d = Document({"id": 123, "coll": Module("Dogs"), "name": "Scout"})
        nd = NamedDocument({
            "id": 123,
            "coll": Module("Dogs"),
            "name": "Scout"
        })
        assert d != nd
