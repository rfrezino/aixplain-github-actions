FROM python:3.11-slim

COPY pyproject.toml .
RUN pip install poetry
RUN poetry install

COPY entrypoint.sh /entrypoint.sh
COPY ./src ./src

ENTRYPOINT ["/entrypoint.sh"]