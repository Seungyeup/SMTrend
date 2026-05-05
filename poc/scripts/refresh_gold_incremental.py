from __future__ import annotations

import argparse
import os
from datetime import date

try:
    from scripts.run_trino_sql_http import execute_sql_text, records_from_result
except ModuleNotFoundError:
    from run_trino_sql_http import execute_sql_text, records_from_result


DDL_SQL = """
CREATE SCHEMA IF NOT EXISTS iceberg.market_iceberg
WITH (location = 's3a://smtrend-iceberg/market_iceberg');

CREATE TABLE IF NOT EXISTS iceberg.market_iceberg.market_bar_1m (
  dt DATE,
  bucket_1m_utc TIMESTAMP(3),
  symbol VARCHAR,
  open_price DOUBLE,
  high_price DOUBLE,
  low_price DOUBLE,
  close_price DOUBLE,
  volume BIGINT,
  tick_count BIGINT
)
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
);

CREATE TABLE IF NOT EXISTS iceberg.market_iceberg.macro_release (
  dt DATE,
  series_id VARCHAR,
  observation_date DATE,
  macro_value DOUBLE,
  release_ts_utc TIMESTAMP(3),
  realtime_start DATE,
  realtime_end DATE
)
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
);

CREATE TABLE IF NOT EXISTS iceberg.market_iceberg.market_macro_aligned_daily (
  symbol VARCHAR,
  close_price DOUBLE,
  volume BIGINT,
  tick_count BIGINT,
  macro_value DOUBLE,
  macro_release_ts_utc TIMESTAMP(3),
  dt DATE
)
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
);

CREATE TABLE IF NOT EXISTS iceberg.market_iceberg.market_macro_correlation_daily (
  symbol VARCHAR,
  rolling_corr_30d DOUBLE,
  dt DATE
)
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
);
"""


def _sql_date_literal(value: date) -> str:
    return f"DATE '{value.isoformat()}'"


def _parse_date_csv(date_csv: str) -> list[date]:
    parsed_dates: list[date] = []
    for raw in date_csv.split(","):
        value = raw.strip()
        if value:
            parsed_dates.append(date.fromisoformat(value))
    return sorted(set(parsed_dates))


def _date_literals(values: list[date]) -> str:
    return ", ".join(_sql_date_literal(value) for value in values)


def _fetch_dates(
    *,
    table_name: str,
    trino_statement_url: str,
    user: str,
    catalog: str,
    schema: str,
) -> list[date]:
    results = execute_sql_text(
        trino_statement_url=trino_statement_url,
        sql_text=f"SELECT CAST(dt AS VARCHAR) AS dt FROM {table_name} GROUP BY 1 ORDER BY 1;",
        user=user,
        catalog=catalog,
        schema=schema,
    )
    rows = records_from_result(results[-1])
    return [date.fromisoformat(str(row["dt"])) for row in rows]


def build_refresh_statements(*, market_dates: list[date], macro_dates: list[date]) -> list[str]:
    statements = [DDL_SQL.strip()]

    if market_dates:
        market_date_sql = _date_literals(market_dates)
        statements.extend(
            [
                f"DELETE FROM iceberg.market_iceberg.market_bar_1m WHERE dt IN ({market_date_sql});",
                (
                    "INSERT INTO iceberg.market_iceberg.market_bar_1m "
                    "SELECT dt, bucket_1m_utc, symbol, open_price, high_price, low_price, close_price, volume, tick_count "
                    f"FROM hive.market.market_bar_1m WHERE dt IN ({market_date_sql});"
                ),
                "ALTER TABLE iceberg.market_iceberg.market_bar_1m EXECUTE optimize;",
            ]
        )

    if macro_dates:
        macro_date_sql = _date_literals(macro_dates)
        statements.extend(
            [
                f"DELETE FROM iceberg.market_iceberg.macro_release WHERE dt IN ({macro_date_sql});",
                (
                    "INSERT INTO iceberg.market_iceberg.macro_release "
                    "SELECT dt, series_id, observation_date, macro_value, release_ts_utc, realtime_start, realtime_end "
                    f"FROM hive.market.macro_release WHERE dt IN ({macro_date_sql});"
                ),
                "ALTER TABLE iceberg.market_iceberg.macro_release EXECUTE optimize;",
            ]
        )

    refresh_start = min(market_dates + macro_dates) if market_dates or macro_dates else None
    if refresh_start is None:
        return statements

    refresh_start_sql = _sql_date_literal(refresh_start)
    statements.extend(
        [
            f"DELETE FROM iceberg.market_iceberg.market_macro_aligned_daily WHERE dt >= {refresh_start_sql};",
            f"""
INSERT INTO iceberg.market_iceberg.market_macro_aligned_daily
WITH market_daily AS (
  SELECT
    dt,
    symbol,
    MAX_BY(close_price, bucket_1m_utc) AS close_price,
    SUM(volume) AS volume,
    SUM(tick_count) AS tick_count
  FROM iceberg.market_iceberg.market_bar_1m
  WHERE dt >= {refresh_start_sql}
  GROUP BY dt, symbol
)
SELECT
  m.symbol,
  m.close_price,
  m.volume,
  m.tick_count,
  MAX_BY(r.macro_value, r.release_ts_utc) AS macro_value,
  MAX(r.release_ts_utc) AS macro_release_ts_utc,
  m.dt AS dt
FROM market_daily m
LEFT JOIN iceberg.market_iceberg.macro_release r
  ON r.series_id = 'DFF'
 AND r.release_ts_utc < CAST(m.dt AS TIMESTAMP(3)) + INTERVAL '1' DAY
GROUP BY m.symbol, m.close_price, m.volume, m.tick_count, m.dt;
""".strip(),
            "ALTER TABLE iceberg.market_iceberg.market_macro_aligned_daily EXECUTE optimize;",
            f"DELETE FROM iceberg.market_iceberg.market_macro_correlation_daily WHERE dt >= {refresh_start_sql};",
            f"""
INSERT INTO iceberg.market_iceberg.market_macro_correlation_daily
SELECT symbol, rolling_corr_30d, dt
FROM (
  SELECT
    symbol,
    corr(close_price, macro_value) OVER (
      PARTITION BY symbol
      ORDER BY dt
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_corr_30d,
    dt
  FROM iceberg.market_iceberg.market_macro_aligned_daily
) aligned
WHERE dt >= {refresh_start_sql};
""".strip(),
            "ALTER TABLE iceberg.market_iceberg.market_macro_correlation_daily EXECUTE optimize;",
        ]
    )
    return statements


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Iceberg gold tables incrementally from Trino external tables")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--market-dates", default="")
    parser.add_argument("--macro-dates", default="")
    parser.add_argument(
        "--trino-statement-url",
        default=os.getenv("TRINO_STATEMENT_URL", "http://localhost:8080/v1/statement"),
    )
    parser.add_argument("--user", default="airflow")
    parser.add_argument("--catalog", default="hive")
    parser.add_argument("--schema", default="market")
    args = parser.parse_args()

    market_dates = _parse_date_csv(args.market_dates) if args.market_dates else []
    macro_dates = _parse_date_csv(args.macro_dates) if args.macro_dates else []

    if not args.plan_only:
        if not market_dates:
            market_dates = _fetch_dates(
                table_name="hive.market.market_bar_1m",
                trino_statement_url=args.trino_statement_url,
                user=args.user,
                catalog=args.catalog,
                schema=args.schema,
            )
        if not macro_dates:
            macro_dates = _fetch_dates(
                table_name="hive.market.macro_release",
                trino_statement_url=args.trino_statement_url,
                user=args.user,
                catalog=args.catalog,
                schema=args.schema,
            )

    statements = build_refresh_statements(market_dates=market_dates, macro_dates=macro_dates)

    if args.plan_only:
        print("\n\n".join(statements))
        return

    for statement in statements:
        execute_sql_text(
            trino_statement_url=args.trino_statement_url,
            sql_text=statement,
            user=args.user,
            catalog=args.catalog,
            schema=args.schema,
        )

    print(
        f"Incremental gold refresh completed: market_dates={len(market_dates)}, macro_dates={len(macro_dates)}"
    )


if __name__ == "__main__":
    main()
