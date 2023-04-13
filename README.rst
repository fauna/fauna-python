A Python driver for `Fauna <https://fauna.com>`_.
==============

.. warning::
    This driver is in beta release and not recommended for production use.
    It operates with the Fauna database service via an API which is also in
    beta release and is not recommended for production use. This driver is
    not compatible with v4 or earlier versions of Fauna. Please feel free to
    contact product@fauna.com to learn about our special Early Access program
    for FQL X.



.. image:: https://img.shields.io/pypi/v/fauna.svg?maxAge=21600
  :target: https://pypi.python.org/pypi/fauna
.. image:: https://img.shields.io/badge/license-MPL_2.0-blue.svg?maxAge=2592000
  :target: https://raw.githubusercontent.com/fauna/fauna-python/main/LICENSE

See the `Fauna Documentation <https://fqlx-beta--fauna-docs.netlify.app/fqlx/beta/>`_ 
for additional information how to configure and query your databases.

This driver can only be used with FQL X, and is not compatible with earlier versions
of FQL. To query your databases with earlier API versions, see
the `faunadb <https://pypi.org/project/faunadb/>`_ package.


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
        create_col = fql('Collection.create({ name: "Dogs" })')
        client.query(create_col)

        # create a document
        create_doc = fql('Dogs.create({ name: "Scout" })')
        res: QuerySuccess = client.query(create_doc)
        doc = res.data
        print(doc)
    except FaunaException as e:
        # handle errors
        print(e)

Query Composition
-----------------

This driver supports query composition with Python primitives, lists, dicts, and other FQL queries. Serialization to and from user-defined classes is not yet supported—for now, adapt your classes into a dict or list prior to using it in composition.

For FQL templates, denote variables with ``${}`` and pass variables as kwargs to ``fql()``. You can escape a variable by prepending an additional ``$``.

.. code-block:: python

    from fauna import fql
    from fauna.client import Client

    def user_by_tin(tin: str):
        return fql('Users.byTin(${tin})', tin=tin)

    def render_user():
        return fql('{ name, address }')

    tin = "123"
    q = fql("""let u = ${user}
    u ${render}
    """, user=user_by_tin(tin), render=render_user())

    client = Client()
    res = client.query(q)

Document Streaming
------------------

Not implemented

Query Stats
------------------

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

    $ make docker-fauna
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
