import abc

from typing import Iterator, Mapping, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorResponse:
  status_code: int
  error_code: str
  error_message: str
  summary: str


class HTTPResponse(abc.ABC):

  @abc.abstractmethod
  def headers(self) -> Mapping[str, str]:
    pass

  @abc.abstractmethod
  def status_code(self) -> int:
    pass

  @abc.abstractmethod
  def json(self) -> Any:
    pass

  @abc.abstractmethod
  def read(self) -> bytes:
    pass

  @abc.abstractmethod
  def iter_bytes(self) -> Iterator[bytes]:
    pass

  @abc.abstractmethod
  def close(self):
    pass

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()


class HTTPClient(abc.ABC):

  @abc.abstractmethod
  def request(
      self,
      method: str,
      url: str,
      headers: Mapping[str, str],
      data: Mapping[str, Any],
  ) -> HTTPResponse:
    pass

  @abc.abstractmethod
  def stream(
      self,
      url: str,
      headers: Mapping[str, str],
      data: Mapping[str, Any],
  ) -> HTTPResponse:
    pass
