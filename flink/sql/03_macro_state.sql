INSERT INTO macro_latest_state
SELECT
  payload.series_id AS series_id,
  payload.`value` AS macro_value,
  payload.release_ts_ms AS release_ts_ms
FROM raw_macro_release;
