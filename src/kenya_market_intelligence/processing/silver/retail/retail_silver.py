
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window

spark = (
    SparkSession.builder.appName("Retail-Bronze-to-Silver").getOrCreate())

BRONZE = "data/bronze/retail/"
SILVER = "data/silver/retail/"

def read_csv(name):
    return spark.read.option("header", True).option(
        "inferSchema", True).csv(BRONZE + name)


def save_parquet(df, name):
    df.write.mode("overwrite").parquet(SILVER + name)


# 1. POS TRANSACTIONS
pos = read_csv("synthetic_pos_transactions.csv")

pos = (
    pos
    .withColumn("transaction_datetime", F.expr("try_cast(transaction_datetime AS TIMESTAMP)"))
    .withColumn("quantity_sold", F.col("quantity_sold").cast("double"))
    .withColumn("unit_price", F.col("unit_price").cast("double"))
    .withColumn("total_amount", F.col("total_amount").cast("double")))

pos_window = Window.partitionBy("transaction_line_id").orderBy("transaction_datetime")
pos = pos.withColumn("row_num", F.row_number().over(pos_window))

pos_duplicates = pos.filter(F.col("row_num") > 1)

pos = pos.filter(F.col("row_num") == 1).drop("row_num")

pos_valid_condition = (
    F.col("transaction_line_id").isNotNull()
    & F.col("transaction_id").isNotNull()
    & F.col("transaction_datetime").isNotNull()
    & F.col("store_id").isNotNull()
    & F.col("product_id").isNotNull()
    & F.col("supplier_id").isNotNull()
    & (F.col("quantity_sold") > 0)
    & (F.col("unit_price") >= 0)
    & (F.col("total_amount") >= 0))

pos_valid = pos.filter(pos_valid_condition)
pos_invalid = pos.filter(~pos_valid_condition)

save_parquet(pos_valid, "pos_transactions")
save_parquet(pos_invalid, "quarantine/pos_invalid")
save_parquet(pos_duplicates, "quarantine/pos_duplicates")


# 2. INVENTORY MOVEMENTS
inventory = read_csv("synthetic_inventory_movements.csv")

inventory = (inventory
    .withColumn("movement_datetime", F.expr("try_cast(movement_datetime AS TIMESTAMP)"))
    .withColumn("quantity_change", F.col("quantity_change").cast("double")))

inventory_window = Window.partitionBy("movement_id").orderBy("movement_datetime")
inventory = inventory.withColumn("row_num", F.row_number().over(inventory_window))
inventory_duplicates = inventory.filter(F.col("row_num") > 1)
inventory = inventory.filter(F.col("row_num") == 1).drop("row_num")

inventory_valid_condition = (
    F.col("movement_id").isNotNull()
    & F.col("movement_datetime").isNotNull()
    & F.col("store_id").isNotNull()
    & F.col("product_id").isNotNull()
    & F.col("movement_type").isin(
        "stock_sale",
        "stock_receipt",
        "stock_count_correction",
        "damaged_goods"
    )
    & F.col("quantity_change").isNotNull())

inventory_valid = inventory.filter(inventory_valid_condition)
inventory_invalid = inventory.filter(~inventory_valid_condition)

save_parquet(inventory_valid, "inventory_movements")
save_parquet(inventory_invalid, "quarantine/inventory_invalid")
save_parquet(inventory_duplicates, "quarantine/inventory_duplicates")


# 3. DIMENSION AND MAPPING DATASETS
products = read_csv("products.csv").dropDuplicates(["product_id"])
products = products.withColumn("base_price", F.col("base_price").cast("double"))
stores = read_csv("stores.csv").dropDuplicates(["store_id"])
suppliers = read_csv("suppliers.csv").dropDuplicates(["supplier_id"])
product_commodity = read_csv("product_commodity_map.csv").dropDuplicates(["product_id", "commodity"])
product_supplier = read_csv("product_supplier_map.csv").dropDuplicates(["product_id", "supplier_id"])

save_parquet(products, "products")
save_parquet(stores, "stores")
save_parquet(suppliers, "suppliers")
save_parquet(product_commodity, "product_commodity_map")
save_parquet(product_supplier, "product_supplier_map")


# 4. SYNTHETIC MARKET OBSERVATIONS
market = read_csv("synthetic_market_observations.csv")

market = (
    market
    .withColumn("date", F.expr("try_cast(date AS DATE)"))
    .withColumn("wholesale_price", F.col("wholesale_price").cast("double"))
    .withColumn("retail_price", F.col("retail_price").cast("double"))
    .withColumn("supply_volume", F.col("supply_volume").cast("double")))

market_valid_condition = (
    F.col("commodity").isNotNull()
    & F.col("market").isNotNull()
    & F.col("county").isNotNull()
    & F.col("date").isNotNull()
    & (F.col("wholesale_price") >= 0)
    & (F.col("retail_price") >= 0)
    & (F.col("supply_volume") >= 0))

market_valid = market.filter(market_valid_condition)
market_invalid = market.filter(~market_valid_condition)

save_parquet(market_valid, "market_observations")
save_parquet(market_invalid, "quarantine/market_invalid")


print("Retail Bronze-to-Silver processing completed.")

for name, df in [
    ("POS transactions", pos_valid),
    ("POS invalid", pos_invalid),
    ("POS duplicates", pos_duplicates),
    ("Inventory movements", inventory_valid),
    ("Inventory invalid", inventory_invalid),
    ("Inventory duplicates", inventory_duplicates),
    ("Products", products),
    ("Stores", stores),
    ("Suppliers", suppliers),
    ("Product-commodity mappings", product_commodity),
    ("Product-supplier mappings", product_supplier),
    ("Market observations", market_valid),
    ("Market invalid", market_invalid),]:
    print(f"{name}: {df.count()} records")

spark.stop()
