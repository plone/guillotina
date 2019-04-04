FROM python:3.7.3-slim
MAINTAINER Plone Community

# Install Python Setuptools
RUN apt-get update -y && \
    apt-get install -y locales git-core gcc g++ netcat libxml2-dev \
    libxslt-dev libz-dev python3-dev

RUN mkdir /app

COPY requirements.txt /requirements.txt
COPY VERSION /VERSION

ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

# Install buildout
RUN pip install -r /requirements.txt
COPY . /app
RUN pip install /app
# RUN pip install guillotina==$(cat VERSION) || pip install guillotina
