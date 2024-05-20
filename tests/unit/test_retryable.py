from typing import List, Optional

import pytest

from fauna.client.retryable import Retryable, ExponentialBackoffStrategy
from fauna.encoding import QuerySuccess, QueryStats
from fauna.errors import ThrottlingError, ServiceError


class Tester:

  def __init__(self, errors: List[Optional[Exception]]):
    self.errors = errors
    self.calls = 0

  def f(self, _=""):
    v = self.errors[self.calls]
    self.calls += 1

    if v is not None:
      raise v

    return QuerySuccess({}, None, None, QueryStats({}), None, None, None, None)


max_attempts = 3
max_backoff = 20


def test_retryable_no_retry():
  tester = Tester([None])
  retryable = Retryable(max_attempts, max_backoff, tester.f)
  r = retryable.run()
  assert r.attempts == 1


def test_retryable_throws_on_non_throttling_error():
  tester = Tester([ServiceError(400, "oops", "not"), None])
  retryable = Retryable(max_attempts, max_backoff, tester.f)
  with pytest.raises(ServiceError):
    retryable.run()


def test_retryable_retries_on_throttling_error():
  tester = Tester([ThrottlingError(429, "oops", "throttled"), None])
  retryable = Retryable(max_attempts, max_backoff, tester.f)
  r = retryable.run()
  assert r.attempts == 2


def test_retryable_throws_when_exceeding_max_attempts():
  err = ThrottlingError(429, "oops", "throttled")
  tester = Tester([err, err, err, err])
  retryable = Retryable(max_attempts, max_backoff, tester.f)
  with pytest.raises(ThrottlingError):
    retryable.run()


def test_strategy_backs_off():
  strat = ExponentialBackoffStrategy(5)
  b1 = strat.wait()
  b2 = strat.wait()
  b3 = strat.wait()
  b4 = strat.wait()
  b5 = strat.wait()

  assert 0.0 <= b1 <= 1.0
  assert 0.0 <= b2 <= 2.0
  assert 0.0 <= b3 <= 4.0
  assert 0.0 <= b4 <= 5.0
  assert 0.0 <= b5 <= 5.0
