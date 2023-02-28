class FaunaException(Exception):
    pass


class ClientError(FaunaException):
    pass


class NetworkError(FaunaException):
    pass


class FaunaError(FaunaException):

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def code(self) -> str:
        return self._code

    @property
    def message(self) -> str:
        return self._message

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ):
        self._status_code = status_code
        self._code = code
        self._message = message

    def __str__(self):
        return f"{self.status_code}: {self.code}\n{self.message}"


class ProtocolError(FaunaError):
    pass


class ServiceError(FaunaError):

    @property
    def summary(self) -> str:
        return self._summary

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        summary: str,
    ):
        super().__init__(status_code, code, message)

        self._summary = summary

    def __str__(self):
        return f"{self._status_code}: {self._code}\n{self._message}\n---\n{self._summary}"
