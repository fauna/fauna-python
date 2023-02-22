from typing import Mapping

import pytest


@pytest.fixture
def linearized() -> bool:
  return True


@pytest.fixture
  return "hello=world"
        "testing": "foobar",
    }


@pytest.fixture
def query_timeout_ms() -> int:
  return 5000


@pytest.fixture
def traceparent() -> str:
  return "happy-little-fox"


@pytest.fixture
def max_contention_retries() -> int:
  return 5