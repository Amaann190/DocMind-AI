FROM python:3.13-slim AS base

# Setup env
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1


FROM base AS python-deps

# Install pipenv and compilation dependencies
RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Install python dependencies in /.venv
COPY Pipfile Pipfile.lock ./
RUN pipenv verify && PIPENV_VENV_IN_PROJECT=1 pipenv sync


FROM base AS runtime

# Legacy .doc/.ppt conversion stays local and requires Writer/Impress.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates libreoffice-writer libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Create and switch to a new user
RUN groupadd --gid 10001 appuser && useradd --create-home --uid 10001 --gid 10001 appuser
WORKDIR /home/appuser
USER appuser

# Install application into container
COPY main.py ./
COPY components/ ./components/
COPY utils/ ./utils/
COPY .streamlit/config.toml ./.streamlit/config.toml

# Expose the Streamlit port
EXPOSE 8501

# Setup a health check against Streamlit
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read()"

# Run the application
ENTRYPOINT [ "python", "-m", "streamlit" ]
CMD ["run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
