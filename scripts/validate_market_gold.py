from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Validate-Market-Gold").getOrCreate()

datasets = {
    "Market prices": "data/gold/market/market_prices",
    "KNBS commodity prices": "data/gold/market/knbs_commodity_prices",
    "KNBS CPI": "data/gold/market/knbs_cpi",
    "Market comparisons": "data/gold/market/market_price_comparison",
}

for name, path in datasets.items():
    df = spark.read.parquet(path)
    print(f"{name}: {df.count()} records")

market = spark.read.parquet(datasets["Market prices"])

print("\nMarket records by source:")
market.groupBy("record_source").count().show()

spark.stop()