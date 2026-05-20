# Ensure repository root is on sys.path so local packages are importable
import os
import sys
import types

ROOT = os.path.dirname(__file__)
PRISMA_MODELS_MODULE = "prisma.models"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide a dummy POLYGON_API_KEY to avoid env-related failures in tests
os.environ.setdefault("POLYGON_API_KEY", "test-key")

# Stub prisma and prisma.models so tests can patch attributes without requiring generated client
# This must be done BEFORE any imports of modules that require prisma stubs
if "prisma" not in sys.modules:
    prisma_module = types.ModuleType("prisma")

    class _PrismaStub:
        auto_register = True

        def __init__(self, auto_register=False):
            pass

    # Json is used in snapshots_ingestor.py
    class _JsonStub(dict):
        pass

    # Error classes used in snapshots_ingestor.py
    class ClientNotConnectedError(Exception):
        pass

    class UniqueViolationError(Exception):
        pass

    # Create prisma.errors module
    prisma_errors = types.ModuleType("prisma.errors")
    prisma_errors.ClientNotConnectedError = ClientNotConnectedError
    prisma_errors.UniqueViolationError = UniqueViolationError

    prisma_module.Prisma = _PrismaStub
    prisma_module.Json = _JsonStub
    sys.modules["prisma"] = prisma_module
    sys.modules["prisma.errors"] = prisma_errors

if PRISMA_MODELS_MODULE not in sys.modules:
    prisma_models = types.ModuleType("prisma.models")

    class _BaseModel:
        @classmethod
        def prisma(cls):
            raise RuntimeError("stub prisma: patch this attribute in tests")

    class Options(_BaseModel):
        pass

    class OptionSnapshot(_BaseModel):
        pass

    prisma_models.Options = Options
    prisma_models.OptionSnapshot = OptionSnapshot
    sys.modules[PRISMA_MODELS_MODULE] = prisma_models
