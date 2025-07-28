"""Options package for strategy-tester."""

from .ingestor import OptionIngestor

ingestor = OptionIngestor()

__all__ = ["ingestor"]
