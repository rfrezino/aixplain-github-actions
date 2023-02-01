FROM python:3.11-slim as base

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base as dev

COPY entrypoint.sh /entrypoint.sh
COPY . .

#ENTRYPOINT ["/entrypoint.sh"]