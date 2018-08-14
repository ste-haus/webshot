FROM alpine:latest

MAINTAINER Erik J. Olson <hello@erikjolson.com>

ENV LIBRARY_PATH=/lib:/usr/lib

RUN apk add --update \
    python3 \
    python-dev \
    py-pip \
    py-pillow \
    chromium \
    chromium-chromedriver \
  && pip3 install --upgrade pip \
  && pip3 install \
    selenium \
  && rm -rf /var/cache/apk/*

RUN mkdir -p /webshot
RUN mkdir -p /screenshots

COPY webshot.py /webshot

ENTRYPOINT ["/webshot/webshot.py"]
