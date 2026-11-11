from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.appName("POS-Validation").getOrCreate()

df = spark.read.parquet("data/silver/retail/quarantine/pos_invalid")

checks = [
    ("Missing product_id", F.col("product_id").isNull()),
    ("Missing supplier_id", F.col("supplier_id").isNull()),
    ("Invalid datetime", F.col("transaction_datetime").isNull()),
    ("Negative quantity", F.col("quantity_sold") <= 0),
    ("Negative unit price", F.col("unit_price") < 0),
]

for name, condition in checks:
    print(f"{name}: {df.filter(condition).count()}")

spark.stop()