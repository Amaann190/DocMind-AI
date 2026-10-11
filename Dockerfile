FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS base
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONUTF8=1

FROM base AS python-deps
RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY Pipfile Pipfile.lock ./
RUN pipenv verify && PIPENV_VENV_IN_PROJECT=1 pipenv sync

FROM base AS runtime
# Local legacy Office conversion; the UI itself is built React assets.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates libreoffice-writer libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH" DOCMIND_DATA_DIR=/home/appuser/data
RUN groupadd --gid 10001 appuser && useradd --create-home --uid 10001 --gid 10001 appuser \
    && mkdir -p /home/appuser/data && chown appuser:appuser /home/appuser/data
WORKDIR /home/appuser
COPY backend/ ./backend/
COPY utils/ ./utils/
COPY --from=frontend /build/dist/ ./frontend/dist/
USER appuser
EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=3).read()"
ENTRYPOINT ["python", "-m", "uvicorn", "backend.app:app"]
CMD ["--host", "0.0.0.0", "--port", "8765"]
