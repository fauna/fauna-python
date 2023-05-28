from typing import Iterator, Optional

from fauna.client.client import Client, QueryOptions
from fauna.query import Query, fql, Page


class QueryIterator:
    """A class to provider an iterator on top of Fauna queries."""

    def __init__(self,
                 client: Client,
                 fql: Query,
                 opts: Optional[QueryOptions] = None):
        """Initializes the QueryIterator

        :param fql: A string, but will eventually be a query expression.
        :param opts: (Optional) Query Options

        :raises TypeError: Invalid param types
        """
        if not isinstance(client, Client):
            err_msg = f"'client' must be a Client but was a {type(client)}. You can build a " \
                        f"Client by calling fauna.client.Client()"
            raise TypeError(err_msg)

        if not isinstance(fql, Query):
            err_msg = f"'fql' must be a Query but was a {type(fql)}. You can build a " \
                       f"Query by calling fauna.fql()"
            raise TypeError(err_msg)

        self.client = client
        self.fql = fql
        self.opts = opts
        self.cursor = None

    def __iter__(self) -> Iterator:
        return self.iter()

    def iter(self) -> Iterator:
        initialResponse = self.client.query(self.fql, self.opts)

        if isinstance(initialResponse.data, Page):
            self.cursor = initialResponse.data.after
            yield initialResponse.data.data

            while self.cursor is not None:
                nextResponse = self.client.query(
                    fql("Set.paginate(${after})", after=self.cursor),
                    self.opts)
                # TODO: `Set.paginate` does not yet return a `@set` tagged value
                #       so we will get back a plain object that might not have
                #       an after property.
                self.cursor = nextResponse.data.get("after")
                yield nextResponse.data.get("data")

        else:
            yield initialResponse.data

    def flatten(self) -> Iterator:
        for page in self.iter():
            try:
                items = iter(page)
                for item in items:
                    yield item

            except Exception as _:
                yield page
