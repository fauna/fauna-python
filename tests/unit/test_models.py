from datetime import datetime

from fauna import Document, NamedDocument, Module

fixed_datetime = datetime.fromisoformat("2023-03-17")


def test_document_required_props(subtests):
    with subtests.test(msg="accepts 'id' str and 'coll' str"):
        Document(id="123", coll="hi", ts=fixed_datetime)

    with subtests.test(msg="accepts 'id' str and 'coll' module"):
        Document(id="123", coll=Module("hi"), ts=fixed_datetime)


def test_document_unwrap(subtests):
    with subtests.test(msg="accepts 'id' str and 'coll' str"):
        d = Document(id="123",
                     coll="Dogs",
                     ts=fixed_datetime,
                     data={"name": "Scout"})
        unwrapped = dict(d)
        assert unwrapped == {"name": "Scout"}


def test_named_document_required_props(subtests):
    with subtests.test(msg="accepts 'name' str and 'coll' str"):
        NamedDocument(name="Python", coll="hi", ts=fixed_datetime)

    with subtests.test(msg="accepts 'name' str and 'coll' module"):
        NamedDocument(name="Python", coll=Module("hi"), ts=fixed_datetime)


def test_document_equality(subtests):
    with subtests.test(msg="Document does not equal NamedDocument"):
        d = Document(id="123",
                     coll="Dogs",
                     ts=fixed_datetime,
                     data={"name": "Scout"})
        nd = NamedDocument(name="Scout",
                           coll="Dogs",
                           ts=fixed_datetime,
                           data={"id": "123"})
        assert d != nd

    with subtests.test(msg="Document equals Document"):
        d1 = Document(id="123",
                      coll="Dogs",
                      ts=fixed_datetime,
                      data={"name": "Scout"})
        d2 = Document(id="123",
                      coll="Dogs",
                      ts=fixed_datetime,
                      data={"name": "Scout"})
        assert d1 == d2

    with subtests.test(msg="NamedDocument equals NamedDocument"):
        nd1 = NamedDocument(name="Scout",
                            coll="Dogs",
                            ts=fixed_datetime,
                            data={"id": "123"})
        nd2 = NamedDocument(name="Scout",
                            coll="Dogs",
                            ts=fixed_datetime,
                            data={"id": "123"})
        assert nd1 == nd2

    with subtests.test(msg="Equality failure with other class does not throw"):
        d1 = Document(id="123",
                      coll="Dogs",
                      ts=fixed_datetime,
                      data={"name": "Scout"})
        other = 123
        _ = d1 == other
        _ = d1 != other
