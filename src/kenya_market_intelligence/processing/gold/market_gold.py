
from pyspark.sql import SparkSession, functions as F

spark = (
    SparkSession.builder
    .appName("Market-Silver-to-Gold")
    .getOrCreate())

# Read Silver datasets
kamis = spark.read.parquet("data/silver/kamis/kamis_market_silver")

synthetic = spark.read.parquet("data/silver/retail/market_observations")

knbs_commodity = spark.read.parquet("data/silver/knbs/commodity_prices_silver")

knbs_cpi = spark.read.parquet("data/silver/knbs/cpi_divisions_silver")

# 1. Unified market prices
kamis = kamis.withColumn("record_source", F.lit("KAMIS"))

market_prices = kamis.unionByName(synthetic)

market_prices = market_prices.withColumn(
    "commodity_key", F.lower(F.trim("commodity"))).withColumn(
    "county_key",
    F.regexp_replace(F.lower(F.trim("county")), r"[^a-z0-9]", ""))

market_prices.write.mode("overwrite").parquet(
    "data/gold/market/market_prices")

# 2. KNBS commodity prices
knbs_commodity.write.mode("overwrite").parquet(
    "data/gold/market/knbs_commodity_prices")

# 3. KNBS CPI
knbs_cpi.write.mode("overwrite").parquet(
    "data/gold/market/knbs_cpi")

# 4. Comparable market prices
market_comparison = (
    market_prices
    .groupBy("commodity_key", "county_key", "date", "record_source")
    .agg(
        F.avg("wholesale_price").alias("avg_wholesale_price"),
        F.avg("retail_price").alias("avg_retail_price"),
        F.count("*").alias("observation_count")))

kamis_prices = market_comparison.filter(
    F.col("record_source") == "KAMIS").alias("k")

synthetic_prices = market_comparison.filter(
    F.col("record_source") == "synthetic").alias("s")

comparison = (
    kamis_prices.join(
        synthetic_prices,
        (
            (F.col("k.commodity_key") == F.col("s.commodity_key"))
            & (F.col("k.county_key") == F.col("s.county_key"))
            & (F.col("k.date") == F.col("s.date"))
        ),
        "inner"
    )
    .select(
        F.col("k.commodity_key").alias("commodity"),
        F.col("k.county_key").alias("county"),
        F.col("k.date").alias("date"),
        F.col("k.avg_retail_price").alias("kamis_retail_price"),
        F.col("s.avg_retail_price").alias("synthetic_retail_price"),
        (
            F.col("k.avg_retail_price")
            - F.col("s.avg_retail_price")
        ).alias("retail_price_difference"),
        F.col("k.observation_count").alias("kamis_observations"),
        F.col("s.observation_count").alias("synthetic_observations")))

comparison.write.mode("overwrite").parquet(
    "data/gold/market/market_price_comparison")

print("Market Gold transformations completed.")

for name, df in [
    ("Unified market prices", market_prices),
    ("KNBS commodity prices", knbs_commodity),
    ("KNBS CPI", knbs_cpi),
    ("Market price comparisons", comparison)
]:
    print(f"{name}: {df.count()} records")

spark.stop()
