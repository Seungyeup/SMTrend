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
