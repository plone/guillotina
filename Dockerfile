FROM python:3.6-slim
MAINTAINER Plone Community

# Update packages
RUN apt-get update -y

# Install Python Setuptools
RUN apt-get install -y locales git-core gcc g++ netcat libxml2-dev libxslt-dev libz-dev

RUN mkdir /app

# Bundle app source
ADD . /app

ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

# Install buildout
RUN cd /app; python3.5 bootstrap-buildout.py

# Run buildout
RUN cd /app; ./bin/buildout -vvv

WORKDIR /app

# Expose
EXPOSE  8080

# Configure and Run
CMD ["/app/bin/guillotina"]
