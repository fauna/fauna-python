import base64
from datetime import datetime, timezone, timedelta

from fauna import fql, Document, NamedDocument


def test_float_roundtrip(client):
  f = 0.1 + 0.1 + 0.1
  assert f != 0.3
  test = fql("${float}", float=f)
  result = client.query(test).data
  assert result == f


def test_32_bit_int_roundtrip(client):
  i = 2147483648
  test = fql("${int}", int=i)
  result = client.query(test).data
  assert result == i


def test_64_bit_int_roundtrip(client):
  lng = 9223372036854775807
  test = fql("${long}", long=lng)
  result = client.query(test).data
  assert result == lng


def test_string_roundtrip(client):
  s = "there and back again"
  test = fql("${str}", str=s)
  result = client.query(test).data
  assert result == s


def test_true_roundtrip(client):
  b = True
  test = fql("${bool}", bool=b)
  result = client.query(test).data
  assert result == b


def test_false_roundtrip(client):
  b = False
  test = fql("${bool}", bool=b)
  result = client.query(test).data
  assert result == b


def test_datetime_utc_roundtrip(client):
  dt = datetime(2023, 2, 10, tzinfo=timezone.utc)
  test = fql("${datetime}", datetime=dt)
  result = client.query(test).data
  assert result == dt


def test_datetime_non_utc_roundtrip(client):
  dt = datetime(2023, 2, 10, tzinfo=timezone(timedelta(hours=2, minutes=0)))
  test = fql("${datetime}", datetime=dt)
  result = client.query(test).data
  assert result == dt


def test_none_roundtrip(client):
  none = None
  test = fql("${none}", none=none)
  result = client.query(test).data
  assert result == none


def test_document_roundtrip(client, a_collection):
  test = client.query(fql("${col}.create({'name':'Scout'})", col=a_collection))
  assert type(test.data) == Document
  result = client.query(fql("${doc}", doc=test.data))
  assert test.data == result.data


def test_named_document_roundtrip(client, a_collection):
  test = client.query(fql("${col}.definition", col=a_collection))
  assert type(test.data) == NamedDocument
  result = client.query(fql("${doc}", doc=test.data))
  assert test.data == result.data


def test_bytes_roundtrip(client):
  test_str = "This is a test string 🚀 with various characters: !@#$%^&*()_+=-`~[]{}|;:'\",./<>?"
  test_bytearray = test_str.encode('utf-8')
  test = client.query(fql("${bts}", bts=test_bytearray))
  assert test.data == test_bytearray
  assert test.data.decode('utf-8') == test_str

  test_bytes = bytes(test_bytearray)
  test = client.query(fql("${bts}", bts=test_bytes))
  assert test.data == test_bytearray
  assert test.data.decode('utf-8') == test_str
