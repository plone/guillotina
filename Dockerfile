FROM python:3.7.3-slim

LABEL name="Guillotina" \
    description="The Python AsyncIO REST API Framework" \
    maintainer="Plone Community"

ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

# Install Python Setuptools
# hadolint ignore=DL3008
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
	locales git-core gcc g++ netcat libxml2-dev \
    	libxslt-dev libz-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app

COPY requirements.txt /requirements.txt
COPY VERSION /VERSION

# Install with pip
# hadolint ignore=DL3013
RUN pip install -r /requirements.txt
COPY . /app
# hadolint ignore=DL3013
RUN pip install /app
# RUN pip install guillotina==$(cat VERSION) || pip install guillotina
