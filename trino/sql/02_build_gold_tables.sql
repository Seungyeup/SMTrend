CREATE SCHEMA IF NOT EXISTS iceberg.market_iceberg
WITH (location = 'hdfs://namenode:9000/data/iceberg/market_iceberg');

DROP TABLE IF EXISTS iceberg.market_iceberg.market_bar_1m;
CREATE TABLE iceberg.market_iceberg.market_bar_1m
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
)
AS
SELECT
  dt,
  bucket_1m_utc,
  symbol,
  open_price,
  high_price,
  low_price,
  close_price,
  volume,
  tick_count
FROM hive.market.market_bar_1m;

DROP TABLE IF EXISTS iceberg.market_iceberg.macro_release;
CREATE TABLE iceberg.market_iceberg.macro_release
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
)
AS
SELECT
  dt,
  series_id,
  observation_date,
  macro_value,
  release_ts_utc,
  realtime_start,
  realtime_end
FROM hive.market.macro_release;

DROP TABLE IF EXISTS iceberg.market_iceberg.market_macro_aligned_daily;
CREATE TABLE iceberg.market_iceberg.market_macro_aligned_daily
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
)
AS
WITH market_daily AS (
  SELECT
    dt,
    symbol,
    MAX_BY(close_price, bucket_1m_utc) AS close_price,
    SUM(volume) AS volume,
    SUM(tick_count) AS tick_count
  FROM iceberg.market_iceberg.market_bar_1m
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

DROP TABLE IF EXISTS iceberg.market_iceberg.market_macro_correlation_daily;
CREATE TABLE iceberg.market_iceberg.market_macro_correlation_daily
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['dt']
)
AS
SELECT
  symbol,
  corr(close_price, macro_value) OVER (
    PARTITION BY symbol
    ORDER BY dt
    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
  ) AS rolling_corr_30d,
  dt
FROM iceberg.market_iceberg.market_macro_aligned_daily;
