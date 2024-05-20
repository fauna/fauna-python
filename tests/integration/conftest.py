import random
import string
from typing import Tuple

import pytest

from fauna import fql, Module
from fauna.client import Client
from fauna.client.utils import _Environment
from fauna.query import Query


def create_collection(name) -> Query:
  return fql('Collection.create({ name: ${name} })', name=name)


def create_database(name) -> Query:
  return fql('Database.create({ name: ${name} })', name=name)


@pytest.fixture
def suffix() -> str:
  letters = string.ascii_lowercase
  return ''.join(random.choice(letters) for _ in range(5))


@pytest.fixture(scope="module")
def client() -> Client:
  return Client()


@pytest.fixture
def scoped_client(scoped_secret) -> Client:
  return Client(secret=scoped_secret)


@pytest.fixture
def scoped_secret(client, suffix) -> str:
  db_name = f"Test_{suffix}"
  client.query(create_database(db_name))
  return f"{_Environment.EnvFaunaSecret()}:{db_name}:admin"


@pytest.fixture
def a_collection(client, suffix) -> Module:
  col_name = f"Test_{suffix}"
  q = create_collection(col_name)
  client.query(q)
  return Module(col_name)


@pytest.fixture
def pagination_collections(client, suffix) -> Tuple[Module, Module]:

  small_name = f"IterTestSmall_{suffix}"
  client.query(create_collection(small_name))
  for i in range(0, 10):
    client.query(
        fql("${mod}.create({ value: ${i} })", mod=Module(small_name), i=i))

  big_name = f"IterTestBig_{suffix}"
  client.query(create_collection(big_name))
  for i in range(0, 20):
    client.query(
        fql("${mod}.create({ value: ${i} })", mod=Module(big_name), i=i))

  return (Module(small_name), Module(big_name))
