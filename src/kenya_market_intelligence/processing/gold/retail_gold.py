
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.appName("Retail-Silver-to-Gold").getOrCreate())

# Read Silver datasets
pos = spark.read.parquet("data/silver/retail/pos_transactions")
inventory = spark.read.parquet("data/silver/retail/inventory_movements")
products = spark.read.parquet("data/silver/retail/products")
stores = spark.read.parquet("data/silver/retail/stores")

# Enrich sales with product and store information
sales = (
    pos
    .withColumn("sales_date", F.to_date("transaction_datetime"))
    .join(products, "product_id", "left")
    .join(stores, "store_id", "left"))

# 1. Daily sales by store
daily_store_sales = (
    sales
    .groupBy("sales_date", "store_id", "store_name", "county")
    .agg(
        F.countDistinct("transaction_id").alias("transaction_count"),
        F.sum("quantity_sold").alias("units_sold"),
        F.sum("total_amount").alias("total_revenue")))

# 2. Product sales performance
product_performance = (
    sales
    .groupBy("product_id", "product_name", "category")
    .agg(
        F.sum("quantity_sold").alias("units_sold"),
        F.sum("total_amount").alias("total_revenue"),
        F.countDistinct("transaction_id").alias("transaction_count"))
    .withColumn(
        "average_selling_price",
        F.when(
            F.col("units_sold") != 0,
            F.col("total_revenue") / F.col("units_sold"))))

# 3. Store sales performance
store_performance = (
    sales
    .groupBy("store_id", "store_name", "county", "region")
    .agg(
        F.countDistinct("transaction_id").alias("transaction_count"),
        F.sum("quantity_sold").alias("units_sold"),
        F.sum("total_amount").alias("total_revenue")))

# 4. Inventory movement summary
inventory_summary = (
    inventory
    .groupBy("store_id", "product_id", "movement_type")
    .agg(
        F.sum("quantity_change").alias("total_quantity_change"),
        F.count("*").alias("movement_count")))

# Write Gold datasets
outputs = {
    "daily_store_sales": daily_store_sales,
    "product_sales_performance": product_performance,
    "store_sales_performance": store_performance,
    "inventory_movement_summary": inventory_summary}

for name, df in outputs.items():
    df.write.mode("overwrite").parquet(f"data/gold/retail/{name}")
    print(f"{name}: {df.count()} records")

print("Retail Gold transformations completed.")

spark.stop()
