"""Shared option data models used by ingestion microservices."""

from dataclasses import dataclass

try:
    from polygon.rest.models.contracts import OptionsContract  # type: ignore[reportMissingImports]
    from polygon.rest.models.snapshot import (
        OptionContractSnapshot,  # type: ignore[reportMissingImports]
    )
except Exception:  # pragma: no cover
    from polygon import OptionContractSnapshot, OptionsContract  # type: ignore

from microservices.shared.models.option_models import OptionSymbol


@dataclass
class OptionIngestParams:
    underlying_asset: str
    price_range: tuple[float, float] | None
    year_range: tuple[int, int]


__all__ = ["OptionsContract", "OptionContractSnapshot", "OptionSymbol", "OptionIngestParams"]
