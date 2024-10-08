FROM python:3.10-alpine

RUN apk add --no-cache --virtual .build-deps postgresql-dev gcc python3-dev musl-dev
RUN apk add libpq

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
RUN apk del --no-cache .build-deps

RUN mkdir -p /src
COPY src/ /src/
RUN pip install -e /src
COPY tests/ /tests/

WORKDIR /src