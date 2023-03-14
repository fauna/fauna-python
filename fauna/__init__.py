__title__ = "Fauna"
__version__ = "0.0.1"
__api_version__ = "10"
__author__ = "Fauna, Inc"
__license__ = "MPL 2.0"
__copyright__ = "2023 Fauna, Inc"

from .client import Client
from .headers import Header
from .http_client import HTTPClient, HTTPResponse, HTTPXClient
from .query_builder import fql, QueryInterpolation
from .models import DocumentReference, Module

global_http_client = None
