CREATE TEMPORARY VIEW curated_market_bar_1m_with_proc AS
SELECT
  symbol,
  window_start,
  close_price,
  volume,
  tick_count,
  'DFF' AS series_id,
  PROCTIME() AS proc_time
FROM curated_market_bar_1m;

INSERT INTO analytics_market_macro_1m
SELECT
  m.symbol,
  m.window_start,
  m.close_price,
  m.volume,
  m.tick_count,
  s.series_id,
  s.macro_value,
  s.release_ts_ms,
  CAST((UNIX_TIMESTAMP(CAST(m.window_start AS STRING)) * 1000 - s.release_ts_ms) / 60000 AS BIGINT) AS macro_age_minutes
FROM curated_market_bar_1m_with_proc AS m
JOIN macro_latest_state AS s
  ON m.series_id = s.series_id;
