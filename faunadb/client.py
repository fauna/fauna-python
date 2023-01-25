from typing import Callable, cast, Any, Optional, SupportsInt, TypeVar, Generic
import os
import platform
import sys
import threading

from time import time
from dataclasses import dataclass, fields, MISSING

import httpx

from faunadb import __api_version__ as api_version
from faunadb import __version__ as pkg_version
from faunadb._json import parse_json_or_none, to_json, _FaunaJSONEncoder
from faunadb.errors import FaunaError, UnexpectedError, _get_or_raise

from faunadb.request_result import RequestResult
# from faunadb.streams import Subscription


class _Constants:

    EndpointProduction = "https://db.fauna.com"
    EndpointPreview = "https://db.fauna-preview.com"
    EndpointLocal = "http://localhost:8443"

    # default fauna client settings
    DefaultEndpoint = EndpointProduction

    # default http client settings
    DefaultHttpConnectTimeout = 1 * 60
    DefaultHttpReadTimeout = 1 * 60
    DefaultHttpWriteTimeout = 1 * 60
    DefaultHttpPoolTimeout = DefaultHttpReadTimeout
    DefaultKeepaliveExpiry = 4  # wait this long before timing out idle connections
    DefaultMaxConnections = 20
    DefaultMaxIdleConnections = 20

    # well-known fauna headers
    HeaderAuthorization = "Authorization"
    HeaderContentType = "Content-Type"
    HeaderTxnTime = "X-Txn-Time"
    HeaderLastSeenTxn = "X-Last-Seen-Txn"
    HeaderLinearized = "X-Linearized"
    HeaderMaxContentionRetries = "X-Max-Contention-Retries"
    HeaderTimeoutMs = "X-Timeout-Ms"
    # HeaderTypeChecking = "X-Fauna-Type-Checking"


T = TypeVar('T')


class _SettingFromEnviron(Generic[T]):

    def __init__(
        self,
        var_name: str,
        default_value: str,
        adapt_from_str: Callable[[str], T],
    ):
        self.__var_name = var_name
        self.__default_value = default_value
        self.__adapt_from_str = adapt_from_str

    def __call__(self) -> T:
        return self.__adapt_from_str(
            os.environ.get(self.__var_name, default=self.__default_value))


def _fancy_bool_from_str(val: str) -> bool:
    return val.lower() in ["1", "true", "yes", "y"]


class _Environment:

    EnvFaunaEndpoint = _SettingFromEnviron(
        "FAUNA_ENDPOINT",
        _Constants.EndpointProduction,
        str,
    )
    """environment variable for Fauna Client HTTP endpoint"""

    EnvFaunaSecret = _SettingFromEnviron(
        "FAUNA_SECRET",
        "",
        str,
    )
    """environment variable for Fauna Client authentication"""

    EnvFaunaMaxConns = _SettingFromEnviron(
        "FAUNA_MAX_CONNS",
        "10",
        int,
    )
    """environment variable for Fauna Client Max Connections per FaunaClient instance"""

    EnvFaunaTimeout = _SettingFromEnviron(
        "FAUNA_TIMEOUT",
        "60",
        int,
    )
    """environment variable for Fauna Client Read-Idle Timeout"""

    EnvFaunaTypeCheckEnabled = _SettingFromEnviron(
        "FAUNA_TYPE_CHECK_ENABLED",
        "1",
        _fancy_bool_from_str,
    )
    """environment variable for Fauna Client Request TypeChecking"""

    EnvFaunaTrackTxnTimeEnabled = _SettingFromEnviron(
        "FAUNA_TRACK_TXN_TIME_ENABLED",
        "1",
        _fancy_bool_from_str,
    )
    """environment variable for Fauna Client automatic tracking of last transaction time"""

    EnvFaunaVerboseDebugEnabled = _SettingFromEnviron(
        "FAUNA_VERBOSE_DEBUG_ENABLED",
        "0",
        _fancy_bool_from_str,
    )
    """environment variable for Fauna Client verbose debugging mode"""


class _HTTPBearerAuth:
    """Creates a bearer base auth object"""

    def auth_header(self):
        return "Bearer {}".format(self.secret)

    def __init__(self, secret):
        self.secret = secret

    def __eq__(self, other):
        return self.secret == getattr(other, 'secret', None)

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers[_Constants.HeaderAuthorization] = self.auth_header()
        return r


class _RuntimeEnvHeader:

    def __init__(self):
        self.pythonVersion = "{0}.{1}.{2}-{3}".format(*sys.version_info)
        self.driverVersion = pkg_version
        self.env = self.getRuntimeEnv()
        self.os = "{0}-{1}".format(platform.system(), platform.release())

    def getRuntimeEnv(self):

        @dataclass
        class EnvChecker:
            name: str
            check: Callable[[], bool]

        env: list[EnvChecker] = [
            EnvChecker(
                name="Netlify",
                check=lambda: "NETLIFY_IMAGES_CDN_DOMAIN" in os.environ,
            ),
            EnvChecker(
                name="Vercel",
                check=lambda: "VERCEL" in os.environ,
            ),
            EnvChecker(
                name="Heroku",
                check=lambda: "PATH" in os.environ and ".heroku" in os.environ[
                    "PATH"],
            ),
            EnvChecker(
                name="AWS Lambda",
                check=lambda: "AWS_LAMBDA_FUNCTION_VERSION" in os.environ),
            EnvChecker(
                name="GCP Cloud Functions",
                check=lambda: "_" in os.environ and "google" in os.environ["_"
                                                                           ],
            ),
            EnvChecker(
                name="GCP Compute Instances",
                check=lambda: "GOOGLE_CLOUD_PROJECT" in os.environ,
            ),
            EnvChecker(
                name="Azure Cloud Functions",
                check=lambda: "WEBSITE_FUNCTIONS_AZUREMONITOR_CATEGORIES" in os
                .environ,
            ),
            EnvChecker(
                name="Azure Compute",
                check=lambda: "ORYX_ENV_TYPE" in os.environ and
                "WEBSITE_INSTANCE_ID" in os.environ and os.environ[
                    "ORYX_ENV_TYPE"] == "AppService",
            ),
        ]

        try:
            recognized = next(e for e in env if e.check())
            if recognized is not None:
                return recognized.name
        except:
            return "Unknown"

    def __str__(self):
        return "driver=python-{0}; runtime=python-{1} env={2}; os={3}".format(
            self.driverVersion, self.pythonVersion, self.env, self.os).lower()


class _LastTxnTime(object):
    """Wraps tracking the last transaction time supplied from the database."""

    def __init__(
        self,
        time: Optional[str] = None,
    ):
        self._lock = threading.Lock()
        self._time = time

    @property
    def time(self):
        """Produces the last transaction time, or, None if not yet updated."""
        with self._lock:
            return self._time

    @property
    def request_header(self):
        """Produces a dictionary with a non-zero `X-Last-Seen-Txn` header; or,
        if one has not yet been set, the empty header dictionary."""
        t = self.time
        if t is None:
            return {}
        return {_Constants.HeaderLastSeenTxn: str(t)}

    def update_txn_time(self, new_txn_time: int):
        """Updates the internal transaction time.
        In order to maintain a monotonically-increasing value, `newTxnTime`
        is discarded if it is behind the current timestamp."""
        with self._lock:
            if self._time is None:
                self._time = new_txn_time
            else:
                self._time = max(self._time, new_txn_time)


@dataclass(frozen=True)
class FaunaClientConfiguration:

    endpoint: str = _Environment.EnvFaunaEndpoint()
    """
    Determines which fauna endpoint to connect to
    Value can be one of 'Production', 'Preview', 'Local' or a fully qualified url providing the fauna endpoint to use.
    Default Behavior
     If this argument is None, then the driver checks the value of env var FAUNA_ENDPOINT.  If the env var is not provided, then defaults to 'Production'
    """

    secret: Optional[str] = _Environment.EnvFaunaSecret()
    """
    A secret for your Fauna DB, used to authorize your queries.
    @see https://docs.fauna.com/fauna/current/security/keys
    """

    max_conns: SupportsInt = _Environment.EnvFaunaMaxConns()
    """
    The maximum number of connections to a make to Fauna from an instance of the FaunaClient

    Default Behavior
     If this argument is None, then the driver checks the value of env var FAUNA_MAX_CONNECTIONS.  If the env var is not provided, then defaults to 10
    """

    track_txn_time_enabled: bool = _Environment.EnvFaunaTrackTxnTimeEnabled()
    """
    Set to true to configure the driver to automatically advance the transaction time associated with this fauna client after every received response

    Default Behavior:
     If this argument is None, then the driver checks the env var FAUNA_TRACK_TXN_TIME_ENABLED.  If that env var is not provided, then defaults to True
    """

    type_check_enabled: bool = _Environment.EnvFaunaTypeCheckEnabled()
    """
    Set to true to configure the fauna-server to run type-checking on the query before executing it
    
    Default Behavior:
     If this argument is None, then the driver checks the env var FAUNA_TYPE_CHECK_ENABLED.  If the env var is not provided, then defaults to True
    """

    timeout_ms: Optional[SupportsInt] = None
    """
    The timeout of each query, in milliseconds. This controls the maximum amount of
    time Fauna will execute your query before marking it failed.
    Can be overridden per-request

    Default Behavior:
     Query timeout is determined by the fauna service
    """

    linearized: Optional[bool] = None
    """
    If true, unconditionally run the query as strictly serialized.
    This affects read-only transactions. Transactions which write
    will always be strictly serialized.
    Can be overridden per-request
    """

    max_contention_retries: Optional[SupportsInt] = None
    """
    The max number of times to retry the query if contention is encountered.
    Can be overridden per-request
    """

    tags: Optional[dict[str, str]] = None
    """
    Tags to add to each query sent by this FaunaClient instance -- these can be used to categorize and search queries in logs/telemetry
    Can be overridden per-request
    """

    traceparent: Optional[str] = None
    """
    A traceparent provided back via logging and telemetry.
    Must match format: https://www.w3.org/TR/trace-context/#traceparent-header
    Can be overridden per-request
    """

    last_txn_time: Optional[str] = None
    """
    An ISO-8601 timestamp to use as the initial value for the last transaction time observed by this client.  (useful primarily from testing contexts)
    If `track_txn_time_enabled` is not set to False then the client will update this value as requests arrive.
    Note: if desired and regardless of the value of track_txn_time_enabled, the effect of this value can be overridden per-request via the `last_txn` request field 
    """


@dataclass(frozen=True)
class _FaunaClientConfiguration:
    """Validated version of FaunaClientConfiguration with non-optional values determined"""

    endpoint: str
    secret: str
    max_conns: int
    track_txn_time_enabled: bool
    type_check_enabled: bool
    timeout_ms: Optional[int] = None
    linearized: Optional[bool] = None
    max_contention_retries: Optional[int] = None
    tags: Optional[dict[str, str]] = None
    traceparent: Optional[str] = None
    last_txn_time: Optional[str] = None

    @classmethod
    def _normalize_endpoint(cls, url: str):
        return url.rstrip("/\\")

    @classmethod
    def from_fauna_client_configuration(cls, obj: FaunaClientConfiguration):
        endpoint = cls._normalize_endpoint(obj.endpoint)

        secret = obj.secret
        if secret is None:
            raise ValueError(
                """You must provide a secret to the fauna driver. Set it
            in an environment variable named FAUNA_SECRET or pass it to the FaunaClient
            constructor.""")

        max_conns = int(obj.max_conns)
        track_txn_time_enabled = obj.track_txn_time_enabled
        type_check_enabled = obj.type_check_enabled
        timeout_ms = int(obj.timeout_ms) if obj.timeout_ms else None
        max_contention_retries = int(
            obj.max_contention_retries) if obj.max_contention_retries else None
        tags = obj.tags
        traceparent = obj.traceparent
        last_txn_time = obj.last_txn_time

        config = _FaunaClientConfiguration(
            endpoint=endpoint,
            secret=secret,
            max_conns=max_conns,
            track_txn_time_enabled=track_txn_time_enabled,
            type_check_enabled=type_check_enabled,
            timeout_ms=timeout_ms,
            max_contention_retries=max_contention_retries,
            tags=tags,
            traceparent=traceparent,
            last_txn_time=last_txn_time,
        )

        return config

    def merging_fauna_request_configuration(
        self,
        obj: Optional['FaunaRequestParameters'] = None,
    ):

        if obj is None:
            return self

        return _FaunaClientConfiguration(
            **self,
            **obj._to_non_default_dict(),
        )


@dataclass(frozen=True)
class FaunaRequestParameters:

    def _to_non_default_dict(self):
        """Return dict representation of this dataclass filtering out any values which were not specified to constructor"""
        d = {}
        for field in fields(self):
            if (field.default is MISSING):
                continue
            d[field.name] = getattr(self, field.name)
        return d

    secret: Optional[str] = None
    """
    A secret for your Fauna DB, used to authorize your queries.
    @see https://docs.fauna.com/fauna/current/security/keys
    """

    last_txn: Optional[str] = None
    """
    The ISO-8601 timestamp of the last transaction the client has previously observed.
    This client will track this by default, however, if you wish to override
    this value for a given request set this value.
    """

    linearized: Optional[bool] = None
    """
    If true, unconditionally run the query as strictly serialized.
    This affects read-only transactions. Transactions which write
    will always be strictly serialized.
    Overrides the optional setting for the client.
    """

    timeout_ms: Optional[SupportsInt] = None
    """
    The timeout to use in this query in milliseconds.
    Overrides the timeout for the client.
    """

    max_contention_retries: Optional[SupportsInt] = None
    """
    The max number of times to retry the query if contention is encountered.
    Overrides the optional setting for the client.
    """

    type_check_enabled: Optional[bool] = None
    """
    Optional. Set to true to configure the fauna-server to run type-checking on the query before executing it
    Default: If this argument is None, then the driver checks the env var FAUNA_TYPE_CHECK_ENABLED.  If the env var is not provided, then defaults to True
    """

    tags: Optional[dict[str, str]] = None
    """
    Tags provided back via logging and telemetry.
    Overrides the optional setting on the client.
    """

    traceparent: Optional[str] = None
    """
    A traceparent provided back via logging and telemetry.
    Must match format: https://www.w3.org/TR/trace-context/#traceparent-header
    Overrides the optional setting for the client.
    """


class FaunaClient(object):
    """
    Directly communicates with Fauna via JSON.
    """

    def __init__(
        self,
        configuration: Optional[FaunaClientConfiguration] = None,
        observer: Optional[Callable[[RequestResult], Any]] = None,
        request_client: httpx.Client = httpx.Client(
            trust_env=False,
            http1=False,
            http2=True,
            timeout=httpx.Timeout(
                connect=_Constants.DefaultHttpConnectTimeout,
                read=_Constants.DefaultHttpReadTimeout,
                write=_Constants.DefaultHttpWriteTimeout,
                pool=_Constants.DefaultHttpPoolTimeout,
            ),
            limits=httpx.Limits(
                max_connections=_Constants.DefaultMaxConnections,
                max_keepalive_connections=_Constants.DefaultMaxIdleConnections,
                keepalive_expiry=_Constants.DefaultKeepaliveExpiry,
            ),
        ),
    ):
        """
        :param configuration:
          Driver configuration parameters
        :param observer:
          Optional. Callback that will be passed a :any:`RequestResult` after every completed request.
        :param request_client:
          Optional, An instance of httpx.Client to use to issue http requests
          Defaults to using a global shared instance
          You may provide your own values for this parameter gain more control of things parameters like network layer timeouts and connection pooling, however sticking with the default shared instance is recommended
        """

        if configuration is None:
            configuration = FaunaClientConfiguration()

        self.configuration = _FaunaClientConfiguration.from_fauna_client_configuration(
            configuration)

        self.observer = observer

        self._auth = _HTTPBearerAuth(self.configuration.secret)

        # immutable, don't mutate it!  that's the only reason this is threadsafe
        self._headers = {
            "Accept-Encoding": "gzip",
            _Constants.HeaderContentType: "application/json;charset=utf-8",
            "X-Fauna-Driver": "python",
            # "X-FaunaDB-API-Version": api_version,
            "X-Driver-Env": str(_RuntimeEnvHeader())
        }

        # driver state -- must be threadsafe
        self.session = request_client
        self._last_txn_time = _LastTxnTime(self.configuration.last_txn_time)

    def sync_last_txn_time(self, new_txn_time: int):
        """
        Sync the freshest timestamp seen by this client.

        This has no effect if staler than currently stored timestamp.
        WARNING: This should be used only when coordinating timestamps across
                multiple clients. Moving the timestamp arbitrarily forward into
                the future will cause transactions to stall.

        :param new_txn_time: the new seen transaction time.
        """
        self._last_txn_time.update_txn_time(new_txn_time)

    def get_last_txn_time(self):
        """
        Get the freshest timestamp reported to this client.
        :return:
        """
        return self._last_txn_time.time

    def get_query_timeout(self):
        """
        Get the query timeout for all queries.
        """
        return self.configuration.timeout_ms

    def new_session_client(
            self,
            configuration: Optional[FaunaRequestParameters] = None,
            observer: Optional[Callable[[RequestResult], Any]] = None,
            request_client: Optional[httpx.Client] = None):
        """
        Create a new client from an existing config with overridden settings

        :param configuration:
          Settings to change on new fauna client instance
        :param observer:
          Callback that will be passed a :any:`RequestResult` after every completed request.
        :param request_client:
          client instance to use, if None will use `request_client` from existing `FaunaClient` instance
        :return:
        """

        merged_config = self.configuration.merging_fauna_request_configuration(
            configuration)

        return FaunaClient(
            configuration=FaunaClientConfiguration(
                **{
                    **merged_config.__dict__,
                    **{
                        "last_txn_time": self.get_last_txn_time()
                    }
                }),
            observer=observer if observer is not None else self.observer,
            request_client=request_client
            if request_client is not None else self.session,
        )

    def query(
        self,
        fql: str,
        arguments: Any = None,
        params: Optional[FaunaRequestParameters] = None,
    ):
        """
        Use the FaunaDB query API.

        :param expression: A query. See :doc:`query` for information on queries.
        :param timeout_millis: Query timeout in milliseconds.
        :return: Converted JSON response.
        """
        return self._execute(
            "POST",
            "/query/1",
            fql=fql,
            arguments=arguments,
            params=params,
        )

    def _execute(
        self,
        action,
        path,
        fql: str,
        arguments: Any,
        params: Optional[FaunaRequestParameters] = None,
    ):
        """Performs an HTTP action, logs it, and looks for errors."""
        c = self.configuration.merging_fauna_request_configuration(params)

        headers = self._headers.copy()

        if c.timeout_ms is not None:
            headers[_Constants.HeaderTimeoutMs] = str(c.timeout_ms)
        if c.track_txn_time_enabled:
            headers.update(self._last_txn_time.request_header)

        request_content: dict[str, Any] = {
            "format": "typed",
            "query": fql,
        }

        # note: we convert to typed format
        # but we don't actually convert this to a json string ...
        # because the whole payload including the query is a json string
        # instead we convert to a pojo containing the tagged format ...
        if arguments is not None:
            request_content["arguments"] = _FaunaJSONEncoder().encode(
                arguments)

        if c.type_check_enabled:
            request_content["typecheck"] = c.type_check_enabled

        start_time = time()
        response = self._perform_request(action, path, request_content,
                                         headers)
        end_time = time()

        if c.track_txn_time_enabled:
            if "X-Txn-Time" in response.headers:
                new_txn_time = int(response.headers["X-Txn-Time"])
                self.sync_last_txn_time(new_txn_time)

        response_raw = response.text
        response_content = parse_json_or_none(response_raw)

        request_result = RequestResult(
            action,
            path,
            request_content,
            response_raw,
            response_content,
            response.status_code,
            response.headers,
            start_time,
            end_time,
        )

        if self.observer is not None:
            self.observer(request_result)

        if response_content is None:
            raise UnexpectedError("Invalid JSON.", request_result)

        FaunaError.raise_for_status_code(request_result)
        return _get_or_raise(request_result, response_content, "data")

    def _perform_request(
        self,
        action: str,
        path: str,
        request_content: Any,
        headers,
    ):
        """Performs an HTTP action."""
        url = self.configuration.endpoint + path

        req = self.session.build_request(
            action,
            url,
            json=request_content,
            headers=headers,
        )

        req = self._auth(req)

        response = self.session.send(req)
        return response
