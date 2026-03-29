CREATE SCHEMA IF NOT EXISTS hive.market;

CREATE TABLE IF NOT EXISTS hive.market.market_bar_1m (
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
  external_location = 'hdfs://namenode:9000/data/silver/market_bar_1m',
  format = 'PARQUET'
);

CREATE TABLE IF NOT EXISTS hive.market.macro_release (
  dt DATE,
  series_id VARCHAR,
  observation_date DATE,
  macro_value DOUBLE,
  release_ts_utc TIMESTAMP(3),
  realtime_start DATE,
  realtime_end DATE
)
WITH (
  external_location = 'hdfs://namenode:9000/data/silver/macro_release',
  format = 'PARQUET'
);
