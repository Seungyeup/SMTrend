-- raw.market.finnhub.tick.v1 -> curated.market.bar.1m.v1
--
-- 목표:
-- - Finnhub quote 이벤트를 symbol 기준 1분 bar 로 집계
-- - open/high/low/close/volume/tick_count 생성

SET 'table.exec.source.idle-timeout' = '5 s';
SET 'table.optimizer.agg-phase-strategy' = 'ONE_PHASE';

CREATE TEMPORARY VIEW market_tick_1m_windowed AS
SELECT
  event_id,
  payload.symbol AS symbol,
  payload.price AS price,
  payload.size AS size,
  event_time,
  window_start,
  window_end
FROM TABLE(
  TUMBLE(TABLE raw_market_tick, DESCRIPTOR(event_time), INTERVAL '1' MINUTE)
);

CREATE TEMPORARY VIEW market_tick_1m_agg AS
SELECT
  symbol,
  window_start,
  window_end,
  MAX(price) AS high_price,
  MIN(price) AS low_price,
  SUM(size) AS volume,
  COUNT(*) AS tick_count
FROM market_tick_1m_windowed
GROUP BY symbol, window_start, window_end;

CREATE TEMPORARY VIEW market_tick_1m_open AS
SELECT
  symbol,
  window_start,
  window_end,
  price AS open_price
FROM (
  SELECT
    symbol,
    window_start,
    window_end,
    price,
    ROW_NUMBER() OVER (
      PARTITION BY symbol, window_start, window_end
      ORDER BY event_time ASC, event_id ASC
    ) AS row_num
  FROM market_tick_1m_windowed
)
WHERE row_num = 1;

CREATE TEMPORARY VIEW market_tick_1m_close AS
SELECT
  symbol,
  window_start,
  window_end,
  price AS close_price
FROM (
  SELECT
    symbol,
    window_start,
    window_end,
    price,
    ROW_NUMBER() OVER (
      PARTITION BY symbol, window_start, window_end
      ORDER BY event_time DESC, event_id DESC
    ) AS row_num
  FROM market_tick_1m_windowed
)
WHERE row_num = 1;

INSERT INTO curated_market_bar_1m
SELECT
  agg.symbol,
  agg.window_start,
  agg.window_end,
  op.open_price,
  agg.high_price,
  agg.low_price,
  cl.close_price,
  agg.volume,
  agg.tick_count
FROM market_tick_1m_agg AS agg
JOIN market_tick_1m_open AS op
  ON agg.symbol = op.symbol
 AND agg.window_start = op.window_start
 AND agg.window_end = op.window_end
JOIN market_tick_1m_close AS cl
  ON agg.symbol = cl.symbol
 AND agg.window_start = cl.window_start
 AND agg.window_end = cl.window_end;
