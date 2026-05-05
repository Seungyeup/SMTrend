SELECT 'market_bar_1m' AS table_name, COUNT(*) AS row_count
FROM hive.market.market_bar_1m
UNION ALL
SELECT 'macro_release' AS table_name, COUNT(*) AS row_count
FROM hive.market.macro_release;
