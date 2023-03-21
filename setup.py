from codecs import open
from os import path

from setuptools import setup

from fauna import __author__ as pkg_author
from fauna import __license__ as pkg_license
from fauna import __version__ as pkg_version

# Load the README file for use in the long description
local_dir = path.abspath(path.dirname(__file__))
with open(path.join(local_dir, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

requires = [
    "iso8601",
    "future",
    "httpx[http2]",
]

extras_require = {
    "lint": ["yapf"],
    "test":
    ["pytest", "pytest-env", "pytest-cov", "pytest-httpx", "pytest-subtests"]
}

setup(
    name="fauna",
    version=pkg_version,
    description="Fauna Python driver for FQL 10+",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/fauna/fauna-python",
    author=pkg_author,
    author_email="priority@fauna.com",
    license=pkg_license,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
    ],
    keywords="faunadb fauna",
    packages=[
        "fauna", "fauna.client", "fauna.encoding", "fauna.errors",
        "fauna.http", "fauna.query"
    ],
    install_requires=requires,
    extras_require=extras_require,
)
