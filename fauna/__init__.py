__title__ = "Fauna"
__version__ = "0.1.0"
__api_version__ = "10"
__author__ = "Fauna, Inc"
__license__ = "MPL 2.0"
__copyright__ = "2023 Fauna, Inc"

from .client import Client
from .headers import Header
from .http import HTTPClient, HTTPResponse, HTTPXClient
from .query_builder import fql, QueryInterpolation
from .models import Document, DocumentReference, NamedDocument, NamedDocumentReference, Module
from .errors import AuthenticationError, ClientError, ProtocolError, ServiceError, AuthorizationError, \
    ServiceInternalError, ServiceTimeoutError, ThrottlingError, QueryTimeoutError, QueryRuntimeError, \
    QueryCheckError

global_http_client = None
