# ACME Salary API. One container: migrate, seed on first boot, serve.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install .

COPY alembic.ini ./
COPY alembic ./alembic
COPY docker-entrypoint.sh ./

RUN useradd --create-home --uid 10001 acme && mkdir -p /data && chown acme /data
USER acme

ENV ACME_DATABASE_URL=sqlite:////data/acme.db \
    PORT=8000
EXPOSE 8000

CMD ["sh", "docker-entrypoint.sh"]
