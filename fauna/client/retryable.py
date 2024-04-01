import abc
from dataclasses import dataclass
from random import random
from time import sleep
from typing import Callable, Optional

from fauna.encoding import QuerySuccess
from fauna.errors import RetryableFaunaException, ClientError


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


@dataclass
class RetryableResponse:
  attempts: int
  response: QuerySuccess


class Retryable:
  """
    Retryable is a wrapper class that acts on a Callable that returns a QuerySuccess.
    """
  _strategy: RetryStrategy
  _error: Optional[Exception]

  def __init__(
      self,
      max_attempts: int,
      max_backoff: int,
      func: Callable[..., QuerySuccess],
      *args,
      **kwargs,
  ):
    self._max_attempts = max_attempts
    self._strategy = ExponentialBackoffStrategy(max_backoff)
    self._func = func
    self._args = args
    self._kwargs = kwargs
    self._error = None

  def run(self) -> RetryableResponse:
    """Runs the wrapped function. Retries up to max_attempts if the function throws a RetryableFaunaException. It propagates
        the thrown exception if max_attempts is reached or if a non-retryable is thrown.

        Returns the number of attempts and the response
        """
    err: Optional[RetryableFaunaException] = None
    attempt = 0
    while True:
      sleep_time = 0.0 if attempt == 0 else self._strategy.wait()
      sleep(sleep_time)

      try:
        attempt += 1
        qs = self._func(*self._args, **self._kwargs)
        return RetryableResponse(attempt, qs)
      except RetryableFaunaException as e:
        if attempt >= self._max_attempts:
          raise e
