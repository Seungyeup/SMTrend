SELECT 'market_bar_1m' AS table_name, COUNT(*) AS row_count
FROM iceberg.market_iceberg.market_bar_1m
UNION ALL
SELECT 'macro_release' AS table_name, COUNT(*) AS row_count
FROM iceberg.market_iceberg.macro_release
UNION ALL
SELECT 'market_macro_aligned_daily' AS table_name, COUNT(*) AS row_count
FROM iceberg.market_iceberg.market_macro_aligned_daily
UNION ALL
SELECT 'market_macro_correlation_daily' AS table_name, COUNT(*) AS row_count
FROM iceberg.market_iceberg.market_macro_correlation_daily;
