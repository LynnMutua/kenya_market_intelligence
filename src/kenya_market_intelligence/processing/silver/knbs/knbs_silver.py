
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \
    .appName("KNBS-Bronze-to-Silver") \
    .getOrCreate()

# Input files
CPI_INPUT = "data/silver/knbs/knbs_cpi_divisions.csv"
COMMODITY_INPUT = "data/silver/knbs/knbs_commodity_prices.csv"

# Silver output folders
CPI_OUTPUT = "data/silver/knbs/cpi_divisions_silver"
COMMODITY_OUTPUT = "data/silver/knbs/commodity_prices_silver"


def clean_strings(df):
    for col in df.columns:
        df = df.withColumn(
            col,
            F.when(
                F.trim(F.col(col)).isin("", "-", "null", "None"),
                None
            ).otherwise(F.trim(F.col(col)))
        )
    return df


def convert_numeric(df, columns):
    for col in columns:
        df = df.withColumn(col, F.col(col).cast("double"))
    return df


def save_silver(df, output_path):
    df.write.mode("overwrite").parquet(output_path)


#CPI DIVISIONS

cpi = spark.read.option("header", True).csv(CPI_INPUT)

print("CPI Bronze records:", cpi.count())

cpi = clean_strings(cpi)

cpi = convert_numeric(
    cpi,
    ["weight_percent", "monthly_change_percent", "annual_change_percent"])

cpi = cpi.withColumn("date", F.to_date("date", "yyyy-MM-dd"))

cpi_invalid = (
    F.col("date").isNull()
    | F.col("division").isNull()
    | (F.col("weight_percent") < 0))

cpi_invalid = F.coalesce(cpi_invalid, F.lit(False))

cpi_invalid_count = cpi.filter(cpi_invalid).count()
cpi = cpi.filter(~cpi_invalid)

#remove only completely identical records
cpi_before = cpi.count()
cpi = cpi.dropDuplicates()
cpi_duplicates = cpi_before - cpi.count()

save_silver(cpi, CPI_OUTPUT)

print("\nCPI SILVER RESULTS")
print("Invalid records:", cpi_invalid_count)
print("Exact duplicates removed:", cpi_duplicates)
print("Final records:", cpi.count())
cpi.printSchema()


# 2. COMMODITY PRICES
commodity = spark.read.option("header", True).csv(COMMODITY_INPUT)

print("\nCommodity Bronze records:", commodity.count())

commodity = clean_strings(commodity)

commodity = convert_numeric(
    commodity,
    [
        "quantity",
        "price_previous_year",
        "price_previous_month",
        "price_current_month",
        "monthly_change_percent",
        "annual_change_percent"])

commodity = commodity.withColumn("date", F.to_date("date", "yyyy-MM-dd"))

commodity_invalid = (
    F.col("date").isNull()
    | F.col("commodity").isNull()
    | (F.col("quantity") < 0)
    | (F.col("price_previous_year") < 0)
    | (F.col("price_previous_month") < 0)
    | (F.col("price_current_month") < 0))

commodity_invalid = F.coalesce(
    commodity_invalid, F.lit(False))

commodity_invalid_count = commodity.filter(
    commodity_invalid).count()

commodity = commodity.filter(~commodity_invalid)

#remove only completely identical records
commodity_before = commodity.count()
commodity = commodity.dropDuplicates()
commodity_duplicates = commodity_before - commodity.count()

save_silver(commodity, COMMODITY_OUTPUT)

print("\nCOMMODITY PRICES SILVER RESULTS")
print("Invalid records:", commodity_invalid_count)
print("Exact duplicates removed:", commodity_duplicates)
print("Final records:", commodity.count())

commodity.printSchema()


print("\nKNBS SILVER TRANSFORMATION COMPLETE")

spark.stop()
