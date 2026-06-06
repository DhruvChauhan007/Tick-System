FROM ubuntu:latest
LABEL authors="Dell"

ENTRYPOINT ["top", "-b"]