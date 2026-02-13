.PHONY: build-IngestOptionsFunction build-IngestSnapshotsFunction build-PingFunction

# Define common build steps for all functions
define build_steps
	uv pip freeze --python 3.12 | grep -v "pyqlib" > $(ARTIFACTS_DIR)/requirements.txt
	pip install -r $(ARTIFACTS_DIR)/requirements.txt -t $(ARTIFACTS_DIR)
	cp -r cli/ $(ARTIFACTS_DIR)/
	cp -r lib/ $(ARTIFACTS_DIR)/
	cp -r options/ $(ARTIFACTS_DIR)/
	cp -r prisma/ $(ARTIFACTS_DIR)/
	cp -r typings/ $(ARTIFACTS_DIR)/
endef

build-IngestOptionsFunction:
	$(call build_steps)

build-IngestSnapshotsFunction:
	$(call build_steps)

build-PingFunction:
	$(call build_steps)


build-PingFunction:
	uv pip freeze --python 3.12 | grep -v "pyqlib" > $(ARTIFACTS_DIR)/requirements.txt
	pip install -r $(ARTIFACTS_DIR)/requirements.txt -t $(ARTIFACTS_DIR)
	cp -r cli/ $(ARTIFACTS_DIR)/
	cp -r lib/ $(ARTIFACTS_DIR)/
	cp -r options/ $(ARTIFACTS_DIR)/
	cp -r prisma/ $(ARTIFACTS_DIR)/
	cp -r typings/ $(ARTIFACTS_DIR)/

build-IngestSnapshotsFunction:
	uv pip freeze --python 3.12 | grep -v "pyqlib" > $(ARTIFACTS_DIR)/requirements.txt
	pip install -r $(ARTIFACTS_DIR)/requirements.txt -t $(ARTIFACTS_DIR)
	cp -r cli/ $(ARTIFACTS_DIR)/
	cp -r lib/ $(ARTIFACTS_DIR)/
	cp -r options/ $(ARTIFACTS_DIR)/
	cp -r prisma/ $(ARTIFACTS_DIR)/
	cp -r typings/ $(ARTIFACTS_DIR)/

