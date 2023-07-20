import os
import platform
import sys
from dataclasses import dataclass
from typing import Callable

from fauna import __version__


class Header:
  LastTxnTs = "X-Last-Txn-Ts"
  Linearized = "X-Linearized"
  MaxContentionRetries = "X-Max-Contention-Retries"
  QueryTimeoutMs = "X-Query-Timeout-Ms"
  Typecheck = "X-Typecheck"
  Tags = "X-Query-Tags"
  Traceparent = "Traceparent"


class _Header:
  AcceptEncoding = "Accept-Encoding"
  Authorization = "Authorization"
  ContentType = "Content-Type"
  Driver = "X-Driver"
  DriverEnv = "X-Driver-Env"
  Format = "X-Format"


class _Auth:
  """Creates an auth helper object"""

  def bearer(self):
    return "Bearer {}".format(self.secret)

  def __init__(self, secret):
    self.secret = secret

  def __eq__(self, other):
    return self.secret == getattr(other, 'secret', None)

  def __ne__(self, other):
    return not self == other


class _DriverEnvironment:

  def __init__(self):
    self.pythonVersion = "{0}.{1}.{2}-{3}".format(*sys.version_info)
    self.driverVersion = __version__
    self.env = self._get_runtime_env()
    self.os = "{0}-{1}".format(platform.system(), platform.release())

  @staticmethod
  def _get_runtime_env():

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
            check=lambda: "PATH" in \
                os.environ and ".heroku" in os.environ["PATH"],
        ),
        EnvChecker(
            name="AWS Lambda",
            check=lambda: "AWS_LAMBDA_FUNCTION_VERSION" in os.environ,
        ),
        EnvChecker(
            name="GCP Cloud Functions",
            check=lambda: "_" in \
                os.environ and "google" in os.environ["_"],
        ),
        EnvChecker(
            name="GCP Compute Instances",
            check=lambda: "GOOGLE_CLOUD_PROJECT" in os.environ,
        ),
        EnvChecker(
            name="Azure Cloud Functions",
            check=lambda: "WEBSITE_FUNCTIONS_AZUREMONITOR_CATEGORIES" in \
                os.environ,
        ),
        EnvChecker(
            name="Azure Compute",
            check=lambda: "ORYX_ENV_TYPE" in os.environ and \
                "WEBSITE_INSTANCE_ID" in os.environ and \
                os.environ["ORYX_ENV_TYPE"] == "AppService",
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
