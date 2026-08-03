FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip && pip install ".[api]"

# The eval harness and its datasets ship in the image. A deployed instance can
# therefore run its own release gate, which is how you confirm the artifact you
# deployed is the artifact you tested.
COPY evals/ ./evals/

FROM base AS test
RUN pip install ".[dev]"
COPY tests/ ./tests/
RUN python -m pytest tests -q && python -m evals.runner

FROM base AS runtime
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
CMD ["uvicorn", "deduction_graph.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
