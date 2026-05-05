CREATE TABLE IF NOT EXISTS raw_macro_release (
  event_id STRING,
  source STRING,
  entity_key STRING,
  event_ts_ms BIGINT,
  ingest_ts_ms BIGINT,
  schema_version STRING,
  payload ROW<
    series_id STRING,
    observation_date STRING,
    `value` DOUBLE,
    release_ts_ms BIGINT,
    realtime_start STRING,
    realtime_end STRING
  >,
  event_time AS TO_TIMESTAMP_LTZ(event_ts_ms, 3),
  WATERMARK FOR event_time AS event_time - INTERVAL '5' MINUTE
) WITH (
  'connector' = 'kafka',
  'topic' = 'raw.macro.fred.release.v1',
  'properties.bootstrap.servers' = 'kafka:9094',
  'properties.group.id' = 'flink-storage-macro-consumer',
  'scan.startup.mode' = 'latest-offset',
  'format' = 'json'
);

CREATE TABLE IF NOT EXISTS curated_market_bar_1m (
  symbol STRING,
  window_start TIMESTAMP_LTZ(3),
  window_end TIMESTAMP_LTZ(3),
  open_price DOUBLE,
  high_price DOUBLE,
  low_price DOUBLE,
  close_price DOUBLE,
  volume BIGINT,
  tick_count BIGINT
) WITH (
  'connector' = 'kafka',
  'topic' = 'curated.market.bar.1m.v1',
  'properties.bootstrap.servers' = 'kafka:9094',
  'properties.group.id' = 'flink-storage-curated-bar-consumer',
  'scan.startup.mode' = 'latest-offset',
  'format' = 'json'
);

CREATE TABLE IF NOT EXISTS silver_market_bar_1m (
  dt DATE,
  bucket_1m_utc TIMESTAMP_LTZ(3),
  symbol STRING,
  open_price DOUBLE,
  high_price DOUBLE,
  low_price DOUBLE,
  close_price DOUBLE,
  volume BIGINT,
  tick_count BIGINT
) WITH (
  'connector' = 'filesystem',
  'path' = 's3a://smtrend-silver/market_bar_1m',
  'format' = 'parquet'
);

CREATE TABLE IF NOT EXISTS silver_macro_release (
  dt DATE,
  series_id STRING,
  observation_date DATE,
  macro_value DOUBLE,
  release_ts_utc TIMESTAMP_LTZ(3),
  realtime_start DATE,
  realtime_end DATE
) WITH (
  'connector' = 'filesystem',
  'path' = 's3a://smtrend-silver/macro_release',
  'format' = 'parquet'
);
