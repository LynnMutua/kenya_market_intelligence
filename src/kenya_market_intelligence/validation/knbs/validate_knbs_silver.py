
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \
    .appName("KNBS-Silver-Validation") \
    .getOrCreate()

datasets = {
    "CPI divisions": "data/silver/knbs/cpi_divisions_silver",
    "Commodity prices": "data/silver/knbs/commodity_prices_silver"}

for name, path in datasets.items():
    df = spark.read.parquet(path)

    print(f"\n--- {name.upper()} VALIDATION ---")

    print("Total records:", df.count())

    print("\nMissing values:")
    for col in df.columns:
        print(col + ":", df.filter(F.col(col).isNull()).count())

    print("\nNegative values:")
    numeric_columns = [
        field.name for field in df.schema.fields
        if field.dataType.simpleString() in ("double", "float", "int", "bigint")]

    for col in numeric_columns:
        print(col + ":", df.filter(F.col(col) < 0).count())

    print("\nDate range:")
    df.select(
        F.min("date").alias("earliest_date"), F.max("date").alias("latest_date")).show()

    print("\nSchema:")
    df.printSchema()

spark.stop()
