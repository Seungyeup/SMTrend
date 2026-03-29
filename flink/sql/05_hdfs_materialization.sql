SET 'execution.checkpointing.interval' = '30 s';

INSERT INTO hdfs_market_bar_1m
SELECT
  CAST(window_start AS DATE) AS dt,
  window_start AS bucket_1m_utc,
  symbol,
  open_price,
  high_price,
  low_price,
  close_price,
  volume,
  tick_count
FROM curated_market_bar_1m;

INSERT INTO hdfs_macro_release
SELECT
  CAST(TO_TIMESTAMP_LTZ(payload.release_ts_ms, 3) AS DATE) AS dt,
  payload.series_id AS series_id,
  CAST(payload.observation_date AS DATE) AS observation_date,
  payload.`value` AS macro_value,
  TO_TIMESTAMP_LTZ(payload.release_ts_ms, 3) AS release_ts_utc,
  CAST(payload.realtime_start AS DATE) AS realtime_start,
  CAST(payload.realtime_end AS DATE) AS realtime_end
FROM raw_macro_release;
