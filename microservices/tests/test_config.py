from microservices.config import get_option_targets_from_env


def test_get_option_targets_from_json(monkeypatch):
    monkeypatch.setenv(
        "OPTION_INGEST_TARGETS",
        '[{"symbol":"NVDA","price_range":[100,200],"year_range":[2026,2027]}]',
    )

    targets = get_option_targets_from_env()

    assert len(targets) == 1
    assert targets[0].underlying_asset == "NVDA"
    assert targets[0].price_range == (100, 200)
    assert targets[0].year_range == (2026, 2027)


def test_get_option_targets_from_symbols(monkeypatch):
    monkeypatch.delenv("OPTION_INGEST_TARGETS", raising=False)
    monkeypatch.setenv("OPTION_INGEST_SYMBOLS", "NVDA, AAPL")
    monkeypatch.setenv("OPTION_INGEST_DEFAULT_YEAR_START", "2027")
    monkeypatch.setenv("OPTION_INGEST_DEFAULT_YEAR_END", "2028")

    targets = get_option_targets_from_env()

    assert [target.underlying_asset for target in targets] == ["NVDA", "AAPL"]
    assert all(target.year_range == (2027, 2028) for target in targets)


def test_get_option_targets_fallback_to_hardcoded(monkeypatch):
    monkeypatch.delenv("OPTION_INGEST_TARGETS", raising=False)
    monkeypatch.delenv("OPTION_INGEST_SYMBOLS", raising=False)

    targets = get_option_targets_from_env()

    assert len(targets) > 0
