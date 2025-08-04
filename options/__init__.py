"""Options package for strategy-tester."""

from options.retriever import OptionRetriever

from .ingestor import OptionIngestor

option_retriever = OptionRetriever()

ingestor = OptionIngestor(option_retriever=option_retriever)

__all__ = ["ingestor"]
