from module_loader import load_package


normalize_quote_response = load_package("ingestion_finnhub", "01_finnhub").normalize_quote_response


def test_normalize_quote_response_shape() -> None:
    quote = normalize_quote_response(
        symbol="AAPL",
        payload={
            "c": 187.21,
            "t": 1_717_171_717,
        },
    )

    assert quote == {
        "symbol": "AAPL",
        "price": 187.21,
        "event_ts_ms": 1_717_171_717_000,
        "size": 1,
    }
