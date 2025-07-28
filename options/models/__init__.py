"""Options models package.

This package provides models and symbols for working with options contracts and snapshots.
"""

from dataclasses import dataclass

from polygon.rest.models.contracts import OptionsContract
from polygon.rest.models.snapshot import OptionContractSnapshot

from .option_models import OptionSymbol


@dataclass
class OptionIngestParams:
    underlying_asset: str
    price_range: tuple[float, float]
    year_range: tuple[int, int]


__all__ = ["OptionsContract", "OptionContractSnapshot", "OptionSymbol", "OptionIngestParams"]
