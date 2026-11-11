from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Inspect-Gold-Inputs").getOrCreate()

datasets = {
    "KAMIS": "data/silver/kamis/kamis_market_silver",
    "KNBS CPI": "data/silver/knbs/cpi_divisions_silver",
    "KNBS commodity prices": "data/silver/knbs/commodity_prices_silver",
    "Retail market observations": "data/silver/retail/market_observations",
}

for name, path in datasets.items():
    print(f"\n{'=' * 50}")
    print(name)
    print(f"{'=' * 50}")

    df = spark.read.parquet(path)
    df.printSchema()
    print("Records:", df.count())
    df.show(3, truncate=False)

spark.stop()
