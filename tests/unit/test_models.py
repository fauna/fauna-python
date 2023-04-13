import datetime

from fauna.query.models import Document, Module, NamedDocument, BaseReference, DocumentReference, \
    NamedDocumentReference, Page

fixed_datetime = datetime.datetime.fromisoformat("2023-03-17")


def test_page_repr():
    p = Page(data=[1, 2], after="feet")
    assert repr(p) == "Page(data=[1, 2],after='feet')"
    assert eval(repr(p)) == p


def test_page_equality():
    p1 = Page(data=[1, 2], after="feet")
    p2 = Page(data=[1, 2], after="feet")
    p3 = Page(data=[{"foo": "bar"}], after="feet")
    assert p1 == p2
    assert p1 != p3


def test_module_repr():
    m = Module("mod_name")
    assert repr(m) == "Module(name='mod_name')"
    assert eval(repr(m)) == m


def test_base_reference_repr():
    br = BaseReference(Module("mod"))
    assert repr(br) == "BaseReference(coll=Module(name='mod'))"
    assert eval(repr(br)) == br


def test_doc_reference_repr():
    dr = DocumentReference(id="123", coll=Module("mod"))
    assert repr(dr) == "DocumentReference(id='123',coll=Module(name='mod'))"
    assert eval(repr(dr)) == dr


def test_named_doc_reference_repr():
    dr = NamedDocumentReference(name="Def", coll=Module("MyCol"))
    assert repr(
        dr) == "NamedDocumentReference(name='Def',coll=Module(name='MyCol'))"
    assert eval(repr(dr)) == dr


def test_doc_repr():
    doc = Document(id="123",
                   coll="MyCol",
                   ts=fixed_datetime,
                   data={"foo": "bar"})
    assert repr(doc) == "Document(id='123'," \
                        "coll=Module(name='MyCol')," \
                        "ts=datetime.datetime(2023, 3, 17, 0, 0)," \
                        "data={'foo':'bar'})"
    assert eval(repr(doc)) == doc


def test_named_doc_repr():
    doc = NamedDocument(name="Things",
                        coll="Foo",
                        ts=fixed_datetime,
                        data={
                            "foo": "bar",
                            "my_date": fixed_datetime
                        })
    assert repr(doc) == "NamedDocument(name='Things'," \
                        "coll=Module(name='Foo')," \
                        "ts=datetime.datetime(2023, 3, 17, 0, 0)," \
                        "data={'foo':'bar','my_date':datetime.datetime(2023, 3, 17, 0, 0)})"
    assert eval(repr(doc)) == doc


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
