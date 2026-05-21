FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
	&& apt-get install -y --no-install-recommends libatomic1 \
	&& rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY uv.lock ./
COPY cli ./cli
COPY microservices ./microservices
COPY prisma ./prisma
COPY typings ./typings

RUN set -eux; \
	uv sync --locked --no-dev; \
	uv run prisma generate --schema=prisma/schema.prisma

CMD ["python", "-c", "from microservices.snapshot_ingestor.service import run; run()"]
