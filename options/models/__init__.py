"""Options models package.

This package provides models and symbols for working with options contracts and snapshots.
"""

from dataclasses import dataclass

try:
    # Prefer real models when available
    from polygon.rest.models.contracts import OptionsContract  # type: ignore[reportMissingImports]
    from polygon.rest.models.snapshot import (
        OptionContractSnapshot,  # type: ignore[reportMissingImports]
    )
except Exception:  # pragma: no cover - typing fallback for editors
    # Fallback to minimal stub types for type checking
    from polygon import OptionContractSnapshot, OptionsContract  # type: ignore

from .option_models import OptionSymbol


@dataclass
class OptionIngestParams:
    underlying_asset: str
    price_range: tuple[float, float] | None
    year_range: tuple[int, int]


__all__ = ["OptionsContract", "OptionContractSnapshot", "OptionSymbol", "OptionIngestParams"]
