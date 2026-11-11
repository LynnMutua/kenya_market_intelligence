from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.appName("Market-Overlap-Check").getOrCreate()

kamis = spark.read.parquet("data/silver/kamis/kamis_market_silver")
synthetic = spark.read.parquet("data/silver/retail/market_observations")

def normalize(df):
    return (
        df.withColumn("commodity_key", F.lower(F.trim("commodity")))
          .withColumn(
              "county_key",
              F.regexp_replace(F.lower(F.trim("county")), r"[^a-z0-9]", "")
          )
    )

k = normalize(kamis)
s = normalize(synthetic)

print("KAMIS date range:")
k.select(F.min("date"), F.max("date")).show()

print("Synthetic date range:")
s.select(F.min("date"), F.max("date")).show()

print("Matching dates:",
      k.select("date").distinct()
       .join(s.select("date").distinct(), "date")
       .count())

print("Matching commodities:",
      k.select("commodity_key").distinct()
       .join(s.select("commodity_key").distinct(), "commodity_key")
       .count())

print("Matching counties:",
      k.select("county_key").distinct()
       .join(s.select("county_key").distinct(), "county_key")
       .count())

print("Matching commodity and county:")
kc = k.select("commodity_key", "county_key").distinct()
sc = s.select("commodity_key", "county_key").distinct()
print(kc.join(sc, ["commodity_key", "county_key"]).count())

print("Matching commodity, county and date:")
kk = k.select("commodity_key", "county_key", "date").distinct()
ss = s.select("commodity_key", "county_key", "date").distinct()
print(kk.join(ss, ["commodity_key", "county_key", "date"]).count())

spark.stop()