.PHONY: setup test ingest-options ingest-snapshots image-build-option image-build-snapshot image-smoke-option image-smoke-snapshot build-IngestOptionsFunction build-IngestSnapshotsFunction build-PingFunction


PYTHON := $(shell command -v python)
DOTENV_OPTIONS_FILE ?= .env.options
DOTENV_SNAPSHOTS_FILE ?= .env.snapshots
IMAGE_TAG ?= local
OPTION_IMAGE ?= strategy-tester-option-ingestor:$(IMAGE_TAG)
SNAPSHOT_IMAGE ?= strategy-tester-snapshot-ingestor:$(IMAGE_TAG)


# Install dependencies using uv
setup:
	uv sync --python $(PYTHON) --extra dev

# Run tests and generate coverage.xml
test: setup
	uv run python -m pytest --cov=./ --cov-report=xml:coverage.xml -q

# Trigger option contracts ingestion
ingest-options:
	DOTENV_PATH=$(DOTENV_OPTIONS_FILE) uv run ingest_options

# Trigger option snapshots ingestion
ingest-snapshots:
	DOTENV_PATH=$(DOTENV_SNAPSHOTS_FILE) uv run ingest_snapshots

# Build option ingestor Docker image
image-build-option:
	docker build -f docker/option-ingestor.Dockerfile -t $(OPTION_IMAGE) .

# Build snapshot ingestor Docker image
image-build-snapshot:
	docker build -f docker/snapshot-ingestor.Dockerfile -t $(SNAPSHOT_IMAGE) .

# Smoke-test option ingestor image imports and target parsing
image-smoke-option: image-build-option
	docker run --rm --env-file $(DOTENV_OPTIONS_FILE) --entrypoint python $(OPTION_IMAGE) -c "from microservices.config import get_option_targets_from_env; targets = get_option_targets_from_env(); print('option-image-ok', len(targets))"

# Smoke-test snapshot ingestor image imports
image-smoke-snapshot: image-build-snapshot
	docker run --rm --env-file $(DOTENV_SNAPSHOTS_FILE) --entrypoint python $(SNAPSHOT_IMAGE) -c "import microservices.snapshot_ingestor.service as s; print('snapshot-image-ok')"

# Define common build steps for all functions
define build_steps
	uv pip freeze --python 3.12 | grep -v "pyqlib" > $(ARTIFACTS_DIR)/requirements.txt
	uv pip install --python 3.12 --target $(ARTIFACTS_DIR) -r $(ARTIFACTS_DIR)/requirements.txt
	cp -r cli/ $(ARTIFACTS_DIR)/
	cp -r microservices/ $(ARTIFACTS_DIR)/
	cp -r prisma/ $(ARTIFACTS_DIR)/
	cp -r typings/ $(ARTIFACTS_DIR)/
endef

build-IngestOptionsFunction:
	$(call build_steps)

build-IngestSnapshotsFunction:
	$(call build_steps)

build-PingFunction:
	$(call build_steps)

