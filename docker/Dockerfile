ARG BASE_IMG=?

FROM $BASE_IMG

WORKDIR /fauna-python
VOLUME /fauna-python

COPY . /fauna-python/

RUN cd /fauna-python && pip install . .[test] .[lint] --use-pep517
