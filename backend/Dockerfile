# Build from the repository root (the API reads database/*.sql and public/samples/):
#   docker build -f backend/Dockerfile -t dealer-portal-api .
#   docker run --env-file backend/.env -p 8000:8000 dealer-portal-api
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
COPY database ./database
COPY public/samples ./public/samples
COPY backend/pyproject.toml backend/alembic.ini ./backend/
COPY backend/alembic ./backend/alembic
COPY backend/app ./backend/app

WORKDIR /srv/backend
# Editable install keeps app/ in place, so paths to ../database and ../public resolve.
RUN pip install --no-cache-dir -e . \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p storage && chown appuser storage
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
# Behind a reverse proxy, set FORWARDED_ALLOW_IPS to the proxy address so client IPs are recorded correctly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
