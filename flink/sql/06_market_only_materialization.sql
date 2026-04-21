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
