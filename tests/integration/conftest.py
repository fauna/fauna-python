import random
import string

import pytest

import fauna
from fauna import fql, Client, QueryBuilder
from fauna.models import Module


def create_collection(name) -> QueryBuilder:
    return fql('Collection.create({ name: ${name} })', name=name)


@pytest.fixture
def suffix() -> str:
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(5))


@pytest.fixture(scope="module")
def client() -> Client:
    return fauna.Client()


@pytest.fixture
def a_collection(client, suffix) -> Module:
    col_name = f"Test_{suffix}"
    q = create_collection(col_name)
    client.query(q)
    return Module(col_name)
