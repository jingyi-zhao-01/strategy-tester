from __future__ import annotations
from typing import Any, Iterable

class RESTClient:
    def __init__(self, api_key: str) -> None: ...
    def list_options_contracts(self, *, underlying_ticker: str | None = ..., contract_type: str | None = ..., expired: bool | None = ..., order: str | None = ..., sort: str | None = ...) -> Iterable[OptionsContract]: ...

class OptionsContract:
    ticker: str | None
    underlying_ticker: str | None
    strike_price: float | None
    expiration_date: Any
    contract_type: str | None

class OptionContractSnapshotDay:
    open: float | None
    close: float | None
    change_percent: float | None
    volume: int | None
    last_updated: int | None

class OptionContractSnapshotGreeks:
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None

class OptionContractSnapshot:
    implied_volatility: float | None
    open_interest: int | None
    day: OptionContractSnapshotDay | None
    greeks: OptionContractSnapshotGreeks | None
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OptionContractSnapshot: ...
