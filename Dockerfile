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
    python3-dev \
    libffi-dev \
    build-base \
  && rm -rf /var/cache/apk/*

RUN python3 -m venv /env

ENV PATH="/env/bin:$PATH"

COPY ./requirements.txt .

RUN pip install --upgrade pip \
  && pip install -r ./requirements.txt

RUN mkdir -p /output

COPY ./src/ .

ENTRYPOINT ["./webshot.py"]

