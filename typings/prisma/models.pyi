from __future__ import annotations
from typing import Any

class _OptionsClient:
    async def find_many(self, *args: Any, **kwargs: Any) -> list[Options]: ...
    async def upsert(self, *args: Any, **kwargs: Any) -> Options: ...

class _OptionSnapshotClient:
    async def upsert(self, *args: Any, **kwargs: Any) -> OptionSnapshot: ...

class Options:
    ticker: str
    underlying_ticker: str
    strike_price: float | None
    expiration_date: Any
    contract_type: str

    @classmethod
    def prisma(cls) -> _OptionsClient: ...

class OptionSnapshot:
    @classmethod
    def prisma(cls) -> _OptionSnapshotClient: ...
