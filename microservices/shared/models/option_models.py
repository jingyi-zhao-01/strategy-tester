from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class OptionSymbol:
    """Data class representing components of an option symbol."""

    underlying: str
    strike: float
    expiration: datetime
    contract_type: Literal["CALL", "PUT"]
