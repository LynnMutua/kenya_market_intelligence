
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("KAMIS-Silver-Validation").getOrCreate()

path = "data/silver/kamis/kamis_market_silver"

df = spark.read.parquet(path)

print("\n--- KAMIS SILVER VALIDATION ---")

# 1. Record count
total = df.count()
print("Total records:", total)

# 2. Duplicate business keys
keys = ["commodity", "classification", "grade", "sex", "market", "county", "date", "wholesale_price", "retail_price"]

duplicates = df.groupBy(keys).count().filter(F.col("count") > 1)
print("Duplicate business keys:", duplicates.count())

# 3. Missing values
print("\nMissing values:")
for col in df.columns:
    print(f"{col}: {df.filter(F.col(col).isNull()).count()}")

# 4. Negative prices and volumes
print("\nNegative values:")
for col in ["wholesale_price", "retail_price", "supply_volume"]:
    print(f"{col}: {df.filter(F.col(col) < 0).count()}")

# 5. Schema
print("\nSchema:")
df.printSchema()

# 6. Date range
print("\nDate range:")
df.select(
    F.min("date").alias("earliest_date"),
    F.max("date").alias("latest_date")).show()

# 7. Commodity coverage
print("\nCommodity coverage:")
df.groupBy("commodity").count().orderBy("commodity").show()

spark.stop()
