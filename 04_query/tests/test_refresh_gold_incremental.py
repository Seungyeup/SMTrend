from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "01_gold_refresh" / "01_refresh_gold_incremental.py"
SPEC = spec_from_file_location("refresh_gold_incremental", MODULE_PATH)
MODULE = module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_refresh_statements_uses_partition_refresh_and_tail_rebuild() -> None:
    statements = MODULE.build_refresh_statements(
        market_dates=[date(2026, 4, 29), date(2026, 4, 30)],
        macro_dates=[date(2026, 4, 28)],
    )

    sql = "\n".join(statements)
    assert "DELETE FROM iceberg.market_iceberg.market_bar_1m WHERE dt IN (DATE '2026-04-29', DATE '2026-04-30')" in sql
    assert "DELETE FROM iceberg.market_iceberg.macro_release WHERE dt IN (DATE '2026-04-28')" in sql
    assert "DELETE FROM iceberg.market_iceberg.market_macro_aligned_daily WHERE dt >= DATE '2026-04-28'" in sql
    assert "DELETE FROM iceberg.market_iceberg.market_macro_correlation_daily WHERE dt >= DATE '2026-04-28'" in sql
