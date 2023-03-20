Fauna Python
==============

.. image:: https://img.shields.io/codecov/c/github/fauna/fauna-python/main.svg?maxAge=21600
  :target: https://codecov.io/gh/fauna/fauna-python
.. image:: https://img.shields.io/pypi/v/fauna.svg?maxAge=21600
  :target: https://pypi.python.org/pypi/fauna
.. image:: https://img.shields.io/badge/license-MPL_2.0-blue.svg?maxAge=2592000
  :target: https://raw.githubusercontent.com/fauna/fauna-python/main/LICENSE

Python driver for `Fauna <https://fauna.com>`_.

.. warning::
    This driver is in beta release and not recommended for production use.
    It operates with the Fauna database service via an API which is also in
    beta release, and is not recommended for production use. This driver is
    not compatible with v4 or earlier versions of Fauna. If you would like
    to participate in the private beta program please contact product@fauna.com.
    

Installation
------------

.. code-block:: bash

    # TODO


Compatibility
-------------

The following versions of Python are supported:

* Python 3.9
* Python 3.10
* Python 3.11

Documentation
-------------

# TODO


Example Usage
-------------

.. code-block:: python

    from fauna import fql, Client

    client = Client()
    client.query(fql('Collection.create({ name: "Dogs" })'))
    client.query(fql('Dogs.create({ name: "Scout" })'))

Query Composition
-----------------

This driver supports query composition with Python primitives, lists, dicts, and other FQL queries. For FQL templates, denote variables with `${}` and pass variables as kwargs to `fql()`.

.. code-block:: python

    from fauna import fql, Client

    def user_by_tin(tin: str):
        return fql('Users.byTin(${tin})', tin=tin)

    def render_user():
        return fql('{ .name, .address }')

    tin = "123"
    q = fql("""let u = ${user}
    u ${render}
    """, user=user_by_tin(tin), render=render_user())
    
    res = client.query(q)

Document Streaming
------------------

Not implemented

Building it yourself
--------------------


Setup
~~~~~

.. code-block:: bash

    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install .


Testing
~~~~~~~

To run the tests you must have a Fauna database available.
Then set the environment variable ``FAUNA_ROOT_KEY`` to your database's root key.
If you use Fauna cloud, this is the password you log in with.

Then run ``make test``.
To test a single test, use e.g. ``python -m unittest tests.test_client.ClientTest.test_ping``.

Tests can also be run via a Docker container with ``FAUNA_ROOT_KEY="your-cloud-secret" make docker-test``
(an alternate Alpine-based Python image can be provided via `RUNTIME_IMAGE`).


Coverage
~~~~~~~~

To run the tests with coverage, install the coverage dependencies with ``pip install .[coverage]``,
and then run ``make coverage``. A summary will be displayed to the terminal, and a detailed coverage report
will be available at ``htmlcov/index.html``.


Contribute
----------

GitHub pull requests are very welcome.


License
-------

Copyright 2023 `Fauna, Inc. <https://fauna.com>`_

Licensed under the Mozilla Public License, Version 2.0 (the
"License"); you may not use this software except in compliance with
the License. You may obtain a copy of the License at

`http://mozilla.org/MPL/2.0/ <http://mozilla.org/MPL/2.0/>`_

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License.


.. _`tests`: https://github.com/fauna/fauna-python/blob/main/tests/
