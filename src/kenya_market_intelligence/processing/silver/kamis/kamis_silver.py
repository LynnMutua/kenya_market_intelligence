
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType

# Paths
INPUT_PATH = "data/bronze/kamis/kamis_market_raw.csv"
OUTPUT_PATH = "data/silver/kamis/kamis_market_silver"

# Spark session
spark = SparkSession.builder.appName("KAMIS-Bronze-to-Silver").getOrCreate()

# Explicit Bronze schema
schema = StructType([
    StructField(col, StringType(), True)
    for col in [
        "commodity", "classification", "grade", "sex",
        "market", "wholesale", "retail", "supply_volume",
        "county", "date"]])

# Read Bronze
df = spark.read.option("header", True).schema(schema).csv(INPUT_PATH)

print("Bronze records:", df.count())

# Standardize strings and missing values
for col in df.columns:
    df = df.withColumn(col,
        F.when(
            F.trim(F.col(col)).isin("", "-", "null", "None"),
            None).otherwise(F.trim(F.col(col))))

# Convert prices and supply volume
for col in ["wholesale", "retail"]:
    df = df.withColumn(col + "_price",
        F.regexp_replace(
            F.col(col), r"(?i)\s*/\s*kg\s*$", "").cast("double"))

df = df.withColumn(
    "supply_volume",
    F.col("supply_volume").cast("double"))

# Convert date
df = df.withColumn(
    "date",
    F.to_date("date", "yyyy-MM-dd"))

# Identify invalid records
invalid = (
    F.col("commodity").isNull()
    | F.col("market").isNull()
    | F.col("county").isNull()
    | F.col("date").isNull()
    | (F.col("wholesale").isNotNull() & F.col("wholesale_price").isNull())
    | (F.col("retail").isNotNull() & F.col("retail_price").isNull())
    | (F.col("wholesale_price") < 0)
    | (F.col("retail_price") < 0)
    | (F.col("supply_volume") < 0))

# Treat unknown conditions as not invalid
invalid = F.coalesce(invalid, F.lit(False))

print("Records before filtering:", df.count())

invalid_count = df.filter(invalid).count()
df = df.filter(~invalid)

# Business-key deduplication
keys = ["commodity", "classification", "grade", "sex", "market", "county", "date", "wholesale_price", "retail_price"]

print("\nDuplicate records:")

duplicate_keys = df.groupBy(keys).count() \
    .filter(F.col("count") > 1).select(*keys)

df.alias("a").join(
    duplicate_keys.alias("b"),
    F.expr("""
        a.commodity <=> b.commodity AND
        a.classification <=> b.classification AND
        a.grade <=> b.grade AND
        a.sex <=> b.sex AND
        a.market <=> b.market AND
        a.county <=> b.county AND
        a.date <=> b.date
    """),
    "inner"
).show(truncate=False)

before_dedup = df.count()
df = df.dropDuplicates(keys)
duplicate_count = before_dedup - df.count()
print("Records after filtering:", before_dedup)
print("Duplicates removed:", duplicate_count)
print("Records after deduplication:", df.count())

# Select Silver columns
silver = df.select(
    "commodity", "classification", "grade", "sex",
    "market", "wholesale_price", "retail_price",
    "supply_volume", "county", "date")

# Save Silver as Parquet
silver.write.mode("overwrite").parquet(OUTPUT_PATH)

# Validation report
print("\nKAMIS SILVER VALIDATION")
print("-----------------------")
print("Invalid records:", invalid_count)
print("Duplicate records:", duplicate_count)
print("Final Silver records:", silver.count())
print("Missing wholesale prices:", silver.filter(F.col("wholesale_price").isNull()).count())
print("Missing retail prices:", silver.filter(F.col("retail_price").isNull()).count())
print("Missing supply volumes:", silver.filter(F.col("supply_volume").isNull()).count())

silver.printSchema()

spark.stop()
