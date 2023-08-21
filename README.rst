The Official Python Driver for `Fauna <https://fauna.com>`_.
============================================================

.. image:: https://img.shields.io/pypi/v/fauna.svg?maxAge=21600
  :target: https://pypi.python.org/pypi/fauna
.. image:: https://img.shields.io/badge/license-MPL_2.0-blue.svg?maxAge=2592000
  :target: https://raw.githubusercontent.com/fauna/fauna-python/main/LICENSE

This driver can only be used with FQL v10, and is not compatible with earlier versions
of FQL. To query your databases with earlier API versions, see
the `faunadb <https://pypi.org/project/faunadb/>`_ package.

See the `Fauna Documentation <https://docs.fauna.com/fauna/current/>`_
for additional information how to configure and query your databases.


Installation
------------

.. code-block:: bash

    pip install fauna


Compatibility
-------------

The following versions of Python are supported:

* Python 3.9
* Python 3.10
* Python 3.11


Basic Usage
-------------
You can expect a ``Client`` instance to have reasonable defaults, like the Fauna endpoint ``https://db.fauna.com`` and a global HTTP client, but you will always need to configure a secret.

You can configure your secret by passing it directly to the client or by setting an environment variable.

Supported Environment Variables:

* ``FAUNA_ENDPOINT``: The Fauna endpoint to use. For example, ``http://localhost:8443``
* ``FAUNA_SECRET``: The Fauna secret to use.

.. code-block:: python

    from fauna import fql
    from fauna.client import Client
    from fauna.encoding import QuerySuccess
    from fauna.errors import FaunaException

    client = Client()
    # The client defaults to using using the value stored FAUNA_SECRET for its secret.
    # Either set the FAUNA_SECRET env variable or retrieve it from a secret store.
    # As a best practice, don't store your secret directly in your code.

    try:
        # create a collection
        q1 = fql('Collection.create({ name: "Dogs" })')
        client.query(q1)

        # create a document
        q2 = fql('Dogs.create({ name: "Scout" })')
        res: QuerySuccess = client.query(q2)
        doc = res.data
        print(doc)
    except FaunaException as e:
        # handle errors
        print(e)

Query Composition
-----------------

This driver supports query composition with Python primitives, lists, dicts, and other FQL queries.

For FQL templates, denote variables with ``${}`` and pass variables as kwargs to ``fql()``. You can escape a variable by prepending an additional ``$``.

.. code-block:: python

    from fauna import fql
    from fauna.client import Client

    client = Client()

    def add_two(x):
        return fql("${x} + 2", x=x)

    q = fql("${y} + 4", y=add_two(2))
    res = client.query(q)
    print(res.data) # 8

Serialization / Deserialization
-------------------------------

Serialization and deserialization with user-defined classes is not yet supported.

When building queries, adapt your classes into dicts or lists prior to using them in composition. When instantiating classes from the query result data, build them from the expected result.

.. code-block:: python

    class MyClass:
        def __init__ (self, my_prop):
            self.my_prop = my_prop

        def to_dict(self):
            return { 'my_prop': self.my_prop }

        @static_method
        def from_result(obj):
            return MyClass(obj['my_prop'])

Client Configuration
--------------------

Timeouts
--------

There are a few different timeout settings that can be configured; each comes with a default setting. We recommend that most applications use the defaults.

Query Timeout
-------------

The query timeout is the time, as ``datetime.timedelta``, that Fauna will spend executing your query before aborting with a ``QueryTimeoutError``.

The query timeout can be set using the ``query_timeout`` option. The default value if you do not provide one is ``DefaultClientBufferTimeout`` (5 seconds).

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(query_timeout=timedelta(seconds=20))

The query timeout can also be set to a different value for each query using the ``QueryOptions.query_timeout`` option. Doing so overrides the client configuration when performing this query.

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client, QueryOptions

    response = client.query(myQuery, QueryOptions(query_timeout=timedelta(seconds=20)))

Client Timeout
--------------

The client timeout is the time, as ``datetime.timedelta``, that the client will wait for a network response before canceling the request. If a client timeout occurs, the driver will throw an instance of ``NetworkError``.

The client timeout is always the query timeout plus an additional buffer. This ensures that the client always waits for at least as long Fauna could work on your query and account for network latency.

The client timeout buffer is configured by setting the ``client_buffer_timeout`` option. The default value for the buffer if you do not provide on is ``DefaultClientBufferTimeout`` (5 seconds), therefore the default client timeout is 10 seconds when considering the default query timeout.

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(client_buffer_timeout=timedelta(seconds=20))


Idle Timeout
------------

The idle timeout is the time, as ``datetime.timedelta``, that a session will remain open after there is no more pending communication. Once the session idle time has elapsed the session is considered idle and the session is closed. Subsequent requests will create a new session; the session idle timeout does not result in an error.

Configure the idle timeout using the ``http_idle_timeout`` option. The default value if you do not provide one is ``DefaultIdleConnectionTimeout`` (5 seconds).

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(http_idle_timeout=timedelta(seconds=6))

> **Note**
> Your application process may continue executing after all requests are completed for the duration of the session idle timeout. To prevent this, it is recommended to call ``Client.close()`` once all requests are complete. It is not recommended to set ``http_idle_timeout`` to small values.

Connect Timeout
---------------

The connect timeout is the maximum amount of time, as ``datetime.timedelta``, to wait until a connection to Fauna is established. If the client is unable to connect within this time frame, a ``ConnectTimeout`` exception is raised.

Configure the connect timeout using the ``http_connect_timeout`` option. The default value if you do not provide one is ``DefaultHttpConnectTimeout`` (5 seconds).

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(http_connect_timeout=timedelta(seconds=6))

Pool Timeout
------------

The pool timeout specifies the maximum amount of time, as ``datetime.timedelta``, to wait for acquiring a connection from the connection pool. If the client is unable to acquire a connection within this time frame, a ``PoolTimeout`` exception is raised. This timeout may fire if 20 connections are currently in use and one isn't released before the timeout is up.

Configure the pool timeout using the ``http_pool_timeout`` option. The default value if you do not provide one is ``DefaultHttpPoolTimeout`` (5 seconds).

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(http_pool_timeout=timedelta(seconds=6))

Read Timeout
------------

The read timeout specifies the maximum amount of time, as ``datetime.timedelta``, to wait for a chunk of data to be received (for example, a chunk of the response body). If the client is unable to receive data within this time frame, a ``ReadTimeout`` exception is raised.

Configure the read timeout using the ``http_read_timeout`` option. The default value if you do not provide one is ``DefaultHttpReadTimeout`` (None).

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(http_read_timeout=timedelta(seconds=6))

Write Timeout
-------------

The write timeout specifies the maximum amount of time, as ``datetime.timedelta``, to wait for a chunk of data to be sent (for example, a chunk of the request body). If the client is unable to send data within this time frame, a ``WriteTimeout`` exception is raised.

Configure the write timeout using the ``http_write_timeout`` option. The default value if you do not provide one is ``DefaultHttpWriteTimeout`` (5 seconds).

.. code-block:: python

    from datetime import timedelta
    from fauna.client import Client

    client = Client(http_write_timeout=timedelta(seconds=6))

Query Stats
-----------

Stats are returned on query responses and ServiceErrors.

.. code-block:: python

    from fauna import fql
    from fauna.client import Client
    from fauna.encoding import QuerySuccess, QueryStats
    from fauna.errors import ServiceError

    client = Client()

    def emit_stats(stats: QueryStats):
        print(f"Compute Ops: {stats.compute_ops}")
        print(f"Read Ops: {stats.read_ops}")
        print(f"Write Ops: {stats.write_ops}")

    try:
        q = fql('Collection.create({ name: "Dogs" })')
        qs: QuerySuccess = client.query(q)
        emit_stats(qs.stats)
    except ServiceError as e:
        if e.stats is not None:
            emit_stats(e.stats)
        # more error handling...

Document Streaming
------------------

Not implemented

Setup
-----

.. code-block:: bash

    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install . .[test] .[lint]


Testing
-------

We use pytest. You can run tests directly or with docker. If you run integration tests directly, you must have fauna running locally.

If you want to run fauna, then run integration tests separately:

.. code-block:: bash

    $ make run-fauna
    $ source venv/bin/activate
    $ make install
    $ make integration-test

To run unit tests locally:

.. code-block:: bash

    $ source venv/bin/activate
    $ make install
    $ make unit-test

To stand up a container and run all tests at the same time:

.. code-block:: bash

    $ make docker-test

See the ``Makefile`` for more.

Coverage
--------

.. code-block:: bash

    $ source venv/bin/activate
    $ make coverage

Contribute
----------

GitHub pull requests are very welcome.


License
-------

Copyright 2023 `Fauna, Inc. <https://fauna.com>`_

Licensed under the Mozilla Public License, Version 2.0 (the
"License"); you may not use this software except in compliance with
the License. You can obtain a copy of the License at

`http://mozilla.org/MPL/2.0/ <http://mozilla.org/MPL/2.0/>`_

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License.


.. _`tests`: https://github.com/fauna/fauna-python/blob/main/tests/
