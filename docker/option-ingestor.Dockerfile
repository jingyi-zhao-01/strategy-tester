FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY uv.lock ./
COPY cli ./cli
COPY microservices ./microservices
COPY prisma ./prisma
COPY typings ./typings

RUN uv sync --locked --no-dev --no-build \
    && prisma generate --schema=prisma/schema.prisma

CMD ["python", "-c", "from microservices.option_ingestor.service import run; run()"]
