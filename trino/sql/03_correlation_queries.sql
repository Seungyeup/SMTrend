SELECT *
FROM iceberg.market_iceberg.market_macro_correlation_daily
WHERE symbol = 'GOOG'
ORDER BY dt DESC
LIMIT 50;

SELECT
  symbol,
  AVG(rolling_corr_30d) AS avg_corr_30d
FROM iceberg.market_iceberg.market_macro_correlation_daily
GROUP BY symbol
ORDER BY avg_corr_30d DESC;
