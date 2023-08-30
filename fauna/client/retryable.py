import abc
from dataclasses import dataclass
from random import random
from time import sleep
from typing import Callable, Any, Optional, Union

from fauna.encoding import QuerySuccess
from fauna.errors import ThrottlingError, ServiceError


@dataclass
class RetryPolicy:
  max_attempts: int = 3
  """An int. The maximum number of attempts."""

  max_backoff: int = 20
  """An int. The maximum backoff in seconds."""


class RetryStrategy:

  @abc.abstractmethod
  def wait(self) -> float:
    pass


class ExponentialBackoffStrategy(RetryStrategy):

  def __init__(self, max_backoff: int):
    self._max_backoff = float(max_backoff)
    self._i = 0.0

  def wait(self) -> float:
    """Returns the number of seconds to wait for the next call."""
    backoff = random() * (2.0**self._i)
    self._i += 1.0
    return min(backoff, self._max_backoff)


class Retryable:
  """
    Retryable is a wrapper class that acts on a Callable that returns a QuerySuccess.
    """
  _strategy: RetryStrategy
  _error: Optional[Exception]

  def __init__(self, policy: RetryPolicy,
               func: Union[Callable[[Any], QuerySuccess],
                           Callable[[], QuerySuccess]], *args, **kwargs):
    self._max_attempts = policy.max_attempts
    self._strategy = ExponentialBackoffStrategy(policy.max_backoff)
    self._func = func
    self._args = args
    self._kwargs = kwargs
    self._error = None

  def run(self) -> QuerySuccess:
    """Runs the wrapped function. Retries up to max_attempts if the function throws a ThrottlingError. It propagates
        the thrown exception if max_attempts is reached or if a non-ThrottlingError is thrown.

        Assigns attempts to QuerySuccess.stats.attempts and ServiceError.stats.attempts
        """
    error: Optional[Exception] = None
    attempt = 0
    for i in range(self._max_attempts):
      sleep_time = 0.0 if attempt == 0 else self._strategy.wait()
      sleep(sleep_time)
      try:
        attempt += 1
        qs = self._func(*self._args, **self._kwargs)
        qs.stats.attempts = attempt
        return qs
      except ThrottlingError as e:
        e.stats.attempts = attempt
        error = e
      except ServiceError as e:
        e.stats.attempts = attempt
        raise e

    raise error
