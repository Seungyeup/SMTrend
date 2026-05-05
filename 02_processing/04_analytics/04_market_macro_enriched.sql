-- curated.market.bar.1m.v1 + state.macro.latest.v1 -> analytics.market_macro.1m.v1
--
-- starter 버전에서는 금리 축 하나만 먼저 붙인다.
-- 즉, DFF 최신 상태와 시장 1분 바를 결합해서
-- "현재 금리 상태 하에서 시장이 어땠는가" 를 볼 수 있게 만든다.

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
JOIN state_macro_latest AS s
  ON m.series_id = s.series_id;
