from typing import cast

import os
from threading import Thread
from time import sleep

from faunadb import query
from faunadb.errors import BadRequest, FaunaError
from tests.helpers import FaunaTestCase


def _on_unhandled_error(event):
    if hasattr(event, "data") and isinstance(event.event, Exception):
        raise event.event
    else:
        raise Exception(event)


class StreamTest(FaunaTestCase):

    @classmethod
    def setUpClass(cls):
        super(StreamTest, cls).setUpClass()
        cls.collection_ref = cls._q(
            query.create_collection({"name": "stream_test_coll"}))["ref"]

        # in order to test max streams on this client, we need to make sure there aren't any other streams open
        cls.max_stream_client = cls.root_client.new_session_client(
            secret=cls.server_key,
            use_separate_connection_pool=True,
        )

    #region Helpers

    @classmethod
    def _create(
        cls,
        n=0,
        **data,
    ):
        data["n"] = n
        return cls._q(query.create(cls.collection_ref, {"data": data}))

    @classmethod
    def _q(
        cls,
        query_json,
    ):
        return cls.client.query(query_json)

    @classmethod
    def stream_sync(cls,
                    expression,
                    options=None,
                    on_start=None,
                    on_error=None,
                    on_version=None,
                    on_history=None,
                    on_set=None):
        if on_error is None:
            on_error = _on_unhandled_error
        return cls.client.stream(
            expression,
            options,
            on_start,
            on_error,
            on_version,
            on_history,
            on_set,
        )

    @classmethod
    def max_stream_sync(cls,
                        expression,
                        options=None,
                        on_start=None,
                        on_error=None,
                        on_version=None,
                        on_history=None,
                        on_set=None):
        if on_error is None:
            on_error = _on_unhandled_error
        return cls.max_stream_client.stream(
            expression,
            options,
            on_start,
            on_error,
            on_version,
            on_history,
            on_set,
        )

    #endregion

    def test_stream_on_document_reference(self):
        ref = self._create()["ref"]

        def on_start(event):
            self.assertEqual(event.type, 'start')
            self.assertTrue(isinstance(event.event, int))
            stream.close()

        stream = self.stream_sync(ref, None, on_start=on_start)
        stream.start()

    def test_stream_on_set(self):

        def on_start(evt):
            self._create()

        def on_set(evt):
            self.assertEqual(evt.type, 'set')
            self.assertEqual(evt.event['action'], 'add')
            stream.close()

        stream = self.stream_sync(query.documents(self.collection_ref),
                                  on_start=on_start,
                                  on_set=on_set)
        stream.start()

    def test_stream_on_set_with_write_that_leads_to_more_streaming(self):

        count = 1

        def on_start(evt):
            self._create()

        def on_set(evt):
            self.assertEqual(evt.type, 'set')
            self.assertEqual(evt.event['action'], 'add')
            nonlocal count
            count += 1
            self._create()
            if count >= 10:
                stream.close()

        stream = self.stream_sync(query.documents(self.collection_ref),
                                  on_start=on_start,
                                  on_set=on_set)
        stream.start()

    def test_stream_max_open_streams(self):
        # note: the max number of streams per connection is set by the server to the value 100.
        # The value of this parameter is not easily visible to driver code in python as its buried deep down in the http2 protocol implementation

        # This test spins up max_streams_per_connection_from_server streams which will not be closed until _all_ of them have observed one message
        # from the server -- if the value is set to max_streams_per_connection_from_server + 1 then the test will hang forever
        self.maxDiff = None
        max_streams_per_connection_from_server = 100

        if os.environ.get("USE_GITHUB_ACTION_OVERRIDES") == "1":
            print("This test is flakey in github action -- skipping for now")
            print("TODO: fix me")
            return

        expected = [i for i in range(max_streams_per_connection_from_server)]
        actual = []
        errors = []

        def threadFn(n):
            ref = self._create(n)["ref"]

            def on_start(event):
                self.assertEqual(event.type, 'start')
                self.assertTrue(isinstance(event.event, int))
                try:
                    self._q(query.update(ref, {"data": {"k": n}}), )
                except Exception as e:
                    errors.append(e)

            def on_version(event):
                self.assertEqual(event.type, 'version')
                actual.append(n)
                self.assertTrue(isinstance(event.event, dict))
                while (len(actual) + len(errors) !=
                       max_streams_per_connection_from_server):
                    sleep(0.1)
                    self.assertEqual(errors, [])
                stream.close()

            stream = self.max_stream_sync(ref,
                                          None,
                                          on_start=on_start,
                                          on_version=on_version)

            try:
                stream.start()
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(max_streams_per_connection_from_server):
            th = Thread(target=threadFn, args=[i])
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
        actual.sort()
        self.assertEqual(errors, [])
        self.assertEqual(actual, expected)

    def test_stream_reject_non_readonly_query(self):
        q = query.create_collection({"name": "c"})

        def on_error(error):
            self.assertEqual(error.type, 'error')
            self.assertTrue(isinstance(error.error, BadRequest))
            self.assertEqual(error.error._get_description(),
                             'Write effect in read-only query expression.')
            stream.close()

        stream = self.stream_sync(q, on_error=on_error)
        stream.start()

    def test_stream_select_fields(self):
        ref = self._create()["ref"]

        fields = {"document", "diff"}

        def on_start(event):
            self.assertEqual(event.type, 'start')
            self.assertTrue(isinstance(event.event, int))
            self._q(query.update(ref, {"data": {"k": "v"}}))

        def on_version(event):
            self.assertEqual(event.type, 'version')
            self.assertTrue(isinstance(event.event, dict))
            self.assertTrue(isinstance(event.txn, int))
            keys = set(event.event.keys())
            self.assertEqual(keys, {"document", "diff"})
            stream.close()

        options = {"fields": list(fields)}
        stream = self.stream_sync(ref,
                                  options,
                                  on_start=on_start,
                                  on_version=on_version)
        stream.start()

    def test_stream_update_last_txn_time(self):
        ref = self._create()["ref"]
        last_txn_time = cast(int, self.client.get_last_txn_time())

        def on_start(event):
            self.assertEqual(event.type, 'start')
            self.assertTrue(
                cast(int, self.client.get_last_txn_time()) > last_txn_time)
            #for start event, last_txn_time maybe be updated to response X-Txn-Time header
            # or event.txn. What is guaranteed is the most recent is used- hence >=.
            self.assertTrue(self.client.get_last_txn_time() >= event.txn)
            self._q(query.update(ref, {"data": {"k": "v"}}))

        def on_version(event):
            self.assertEqual(event.type, 'version')
            self.assertEqual(event.txn, self.client.get_last_txn_time())
            stream.close()

        stream = self.stream_sync(ref,
                                  on_start=on_start,
                                  on_version=on_version)
        stream.start()

    def test_stream_handle_request_failures(self):
        stream = None

        def on_error(event):
            self.assertEqual(event.type, 'error')
            self.assertTrue(isinstance(event.error, BadRequest))
            self.assertEqual(
                event.error._get_description(),
                'Expected a Document Ref or Version, or a Set Ref, got String.'
            )

        stream = self.stream_sync('invalid stream', on_error=on_error)
        stream.start()

    def test_start_active_stream(self):
        ref = self._create()["ref"]

        def on_start(event):
            self.assertEqual(event.type, 'start')
            self.assertTrue(isinstance(event.event, int))
            self.assertRaises(FaunaError, lambda: stream.start())
            stream.close()

        stream = self.stream_sync(ref, None, on_start=on_start)
        stream.start()

    def test_stream_auth_revalidation(self):
        ref = self._create()["ref"]

        server_key = self.root_client.query(
            query.create_key({
                "database": self.db_ref,
                "role": "server"
            }))
        client = self.root_client.new_session_client(
            secret=server_key["secret"])

        def on_start(event):
            self.assertEqual(event.type, 'start')
            self.assertTrue(isinstance(event.event, int))
            self.root_client.query(query.delete(server_key["ref"]))
            self.client.query(query.update(ref, {"data": {"k": "v"}}))

        def on_error(event):
            self.assertEqual(event.type, 'error')
            self.assertEqual(event.code, 'permission denied')
            self.assertEqual(event.description,
                             'Authorization lost during stream evaluation.')
            stream.close()

        stream = client.stream(ref, on_start=on_start, on_error=on_error)
        stream.start()
