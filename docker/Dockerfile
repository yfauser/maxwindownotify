FROM python:2.7
MAINTAINER Yves Fauser <yfauser@yahoo.de>
LABEL Description="This is the Dockerfile to create a Docker container for maxwindownotify (github.com/yfauser/maxwindownotify)"
RUN ["pip", "install", "maxwindownotify"]
ENTRYPOINT ["maxwindownotify"]
CMD ["--help"]


