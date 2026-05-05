from datetime import date

from scripts.refresh_gold_incremental import build_refresh_statements


def test_build_refresh_statements_uses_partition_refresh_and_tail_rebuild() -> None:
    statements = build_refresh_statements(
        market_dates=[date(2026, 4, 29), date(2026, 4, 30)],
        macro_dates=[date(2026, 4, 28)],
    )

    sql = "\n".join(statements)
    assert "DELETE FROM iceberg.market_iceberg.market_bar_1m WHERE dt IN (DATE '2026-04-29', DATE '2026-04-30');" in sql
    assert "DELETE FROM iceberg.market_iceberg.macro_release WHERE dt IN (DATE '2026-04-28');" in sql
    assert "DELETE FROM iceberg.market_iceberg.market_macro_aligned_daily WHERE dt >= DATE '2026-04-28';" in sql
    assert "DELETE FROM iceberg.market_iceberg.market_macro_correlation_daily WHERE dt >= DATE '2026-04-28';" in sql
