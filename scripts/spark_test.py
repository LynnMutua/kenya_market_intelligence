from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("KenyaMarketIntelligence") \
    .master("local[*]") \
    .getOrCreate()

print("Spark Version:", spark.version)

data = [("Dry Maize", 44.44), ("Wheat", 85.00)]
df = spark.createDataFrame(data, ["commodity", "price"])

df.show()

spark.stop()