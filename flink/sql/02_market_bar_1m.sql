SET 'table.exec.source.idle-timeout' = '5 s';

INSERT INTO curated_market_bar_1m
SELECT
  payload.symbol AS symbol,
  window_start,
  window_end,
  MIN(payload.price) AS open_price,
  MAX(payload.price) AS high_price,
  MIN(payload.price) AS low_price,
  MAX(payload.price) AS close_price,
  SUM(payload.size) AS volume,
  COUNT(*) AS tick_count
FROM TABLE(
  TUMBLE(TABLE raw_market_tick, DESCRIPTOR(event_time), INTERVAL '1' MINUTE)
)
GROUP BY payload.symbol, window_start, window_end;
