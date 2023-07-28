__title__ = "Fauna"
__version__ = "0.8.0"
__api_version__ = "10"
__author__ = "Fauna, Inc"
__license__ = "MPL 2.0"
__copyright__ = "2023 Fauna, Inc"

from fauna.query import fql, Document, DocumentReference, NamedDocument, NamedDocumentReference, NullDocument, Module, Page

global_http_client = None
