# Ensure repository root is on sys.path so 'options' and 'lib' packages are importable
import os
import sys
import types

ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide a dummy POLYGON_API_KEY to avoid env-related failures in tests
os.environ.setdefault("POLYGON_API_KEY", "test-key")

# Stub prisma.models so tests can patch attributes without requiring generated client
if "prisma.models" not in sys.modules:
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
    sys.modules["prisma.models"] = prisma_models
