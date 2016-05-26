FROM python:3.5-slim
MAINTAINER Plone Community

# Update packages
RUN apt-get update -y

# Install Python Setuptools
RUN apt-get install -y locales git-core gcc netcat

RUN mkdir /app

# Bundle app source
ADD . /app

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Install buildout
RUN cd /app; python3.5 bootstrap-buildout.py

# Run buildout
RUN cd /app; ./bin/buildout -vvv

# Expose
EXPOSE  8080

# Configure and Run
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/app/bin/server"]
