from codecs import open
from os import path

from setuptools import setup

from fauna import __author__ as pkg_author
from fauna import __license__ as pkg_license
from fauna import __version__ as pkg_version

# Load the README file for use in the long description
local_dir = path.abspath(path.dirname(__file__))
with open(path.join(local_dir, "README.md"), encoding="utf-8") as f:
  long_description = f.read()

requires = [
    "iso8601==2.1.0",
    "future==1.0.0",
    "httpx[http2]==0.28.*",
]

extras_require = {
    "lint": ["yapf==0.40.1"],
    "test": [
        "pytest==8.1.1",
        "pytest-env==1.1.3",
        "pytest-cov==5.0.0",
        "pytest-httpx==0.35.0",
        "pytest-subtests==0.12.1",
    ]
}

setup(
    name="fauna",
    version=pkg_version,
    description="Fauna Python driver for FQL 10+",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fauna/fauna-python",
    author=pkg_author,
    author_email="priority@fauna.com",
    license=pkg_license,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
    ],
    keywords="faunadb fauna",
    packages=[
        "fauna",
        "fauna.client",
        "fauna.encoding",
        "fauna.errors",
        "fauna.http",
        "fauna.query",
    ],
    python_requires='>=3.9, <4',
    install_requires=requires,
    extras_require=extras_require,
)
