from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class OptionSymbolComponents:
    """
    Data class representing components of an option symbol

    Example:
        For symbol 'O:SE250808C00165000':
        - underlying: 'SE'
        - expiration: datetime(2025, 8, 8)
        - contract_type: 'CALL'
        - strike: 165.0
    """

    underlying: str
    expiration: datetime
    contract_type: Literal["CALL", "PUT"]
    strike: float
