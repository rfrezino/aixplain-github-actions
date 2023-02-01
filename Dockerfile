FROM python:3.11-slim as base

COPY pyproject.toml .
RUN pip install poetry
RUN poetry install

FROM base as dev

COPY entrypoint.sh /entrypoint.sh
COPY ./src ./src

ENTRYPOINT ["/entrypoint.sh"]