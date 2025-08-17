"""Options package for strategy-tester.

Avoid side effects at import time by not instantiating objects that may
require external services (e.g., database, external APIs). Consumers can
import classes/functions directly and instantiate as needed.
"""

__all__ = []
