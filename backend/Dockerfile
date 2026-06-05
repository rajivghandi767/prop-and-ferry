FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY dev-requirements.txt /app/

RUN pip install --no-cache-dir -r dev-requirements.txt
