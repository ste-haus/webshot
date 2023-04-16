FROM alpine:latest

MAINTAINER Erik J. Olson <hello@erikjolson.com>

WORKDIR /usr/src/app

ENV LIBRARY_PATH=/lib:/usr/lib

RUN apk add --update \
    python3 \
    py-pip \
    py-pillow \
    chromium \
    chromium-chromedriver \
    chromium-swiftshader \
  && rm -rf /var/cache/apk/*

COPY ./requirements.txt .
RUN pip3 install --upgrade pip \
  && pip install -r ./requirements.txt

RUN mkdir -p /output

COPY ./src/ .

ENTRYPOINT ["./webshot.py"]

