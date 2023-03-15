import pytest

from fauna import Document, NamedDocument, Module, DocumentReference, NamedDocumentReference


def test_document_required_props(subtests):
    with subtests.test(msg="accepts 'id' str and 'coll' str"):
        Document({"id": "123", "coll": "hi"})

    with subtests.test(msg="accepts 'id' str and 'coll' module"):
        Document({"id": "123", "coll": Module("hi")})

    with subtests.test(msg="must contain 'coll'"):
        with pytest.raises(ValueError,
                           match="Data must contain the 'coll' and 'id' keys"):
            Document({"id": "123"})

    with subtests.test(msg="must contain 'id'"):
        with pytest.raises(ValueError,
                           match="Data must contain the 'coll' and 'id' keys"):
            Document({"coll": "hi"})

    with subtests.test(msg="'coll' must be a str or module"):
        with pytest.raises(
                TypeError,
                match=
                "'coll' should be of type Module or str, but was <class 'int'>"
        ):
            Document({"id": "123", "coll": 123})


def test_named_document_required_props(subtests):
    with subtests.test(msg="accepts 'name' str and 'coll' str"):
        NamedDocument({"name": "Python", "coll": "hi"})

    with subtests.test(msg="accepts 'name' str and 'coll' module"):
        NamedDocument({"name": "Python", "coll": Module("hi")})

    with subtests.test(msg="must contain 'coll'"):
        with pytest.raises(
                ValueError,
                match="Data must contain the 'coll' and 'name' keys"):
            NamedDocument({"name": "123"})

    with subtests.test(msg="must contain 'id'"):
        with pytest.raises(
                ValueError,
                match="Data must contain the 'coll' and 'name' keys"):
            NamedDocument({"coll": "hi"})

    with subtests.test(msg="'coll' must be a str or module"):
        with pytest.raises(
                TypeError,
                match=
                "'coll' should be of type Module or str, but was <class 'int'>"
        ):
            NamedDocument({"name": "Python", "coll": 123})


def test_ref_does_not_conflict(subtests):
    with subtests.test(msg="Document does not conflict"):
        d = Document({"id": "123", "coll": Module("Dogs"), "ref": "my_ref"})
        assert d.ref == DocumentReference(Module("Dogs"), "123")
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
        d = Document({"id": "123", "coll": Module("Dogs"), "name": "Scout"})
        nd = NamedDocument({
            "id": "123",
            "coll": Module("Dogs"),
            "name": "Scout"
        })
        assert d != nd

    with subtests.test(msg="Document equals Document"):
        d1 = Document({"id": "123", "coll": Module("Dogs"), "name": "Scout"})
        d2 = Document({"id": "123", "coll": Module("Dogs"), "name": "Scout"})
        assert d1 == d2

    with subtests.test(msg="NamedDocument equals NamedDocument"):
        nd1 = NamedDocument({
            "id": "123",
            "coll": Module("Dogs"),
            "name": "Scout"
        })
        nd2 = NamedDocument({
            "id": "123",
            "coll": Module("Dogs"),
            "name": "Scout"
        })
        assert nd1 == nd2
