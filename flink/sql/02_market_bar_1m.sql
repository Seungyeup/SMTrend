SET 'table.exec.source.idle-timeout' = '5 s';
SET 'table.optimizer.agg-phase-strategy' = 'ONE_PHASE';

INSERT INTO curated_market_bar_1m
SELECT
  payload.symbol AS symbol,
  event_time AS window_start,
  event_time + INTERVAL '1' MINUTE AS window_end,
  payload.price AS open_price,
  payload.price AS high_price,
  payload.price AS low_price,
  payload.price AS close_price,
  payload.size AS volume,
  CAST(1 AS BIGINT) AS tick_count
FROM raw_market_tick;
