from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.appName("Validate-Retail-Gold").getOrCreate()

pos = spark.read.parquet("data/silver/retail/pos_transactions")
inventory = spark.read.parquet("data/silver/retail/inventory_movements")

daily = spark.read.parquet("data/gold/retail/daily_store_sales")
products = spark.read.parquet("data/gold/retail/product_sales_performance")
stores = spark.read.parquet("data/gold/retail/store_sales_performance")
movements = spark.read.parquet("data/gold/retail/inventory_movement_summary")

def total(df, column):
    return df.agg(F.sum(column)).first()[0] or 0

print("POS Silver revenue:", total(pos, "total_amount"))
print("Daily Gold revenue:", total(daily, "total_revenue"))
print("Product Gold revenue:", total(products, "total_revenue"))
print("Store Gold revenue:", total(stores, "total_revenue"))

print("\nPOS Silver quantity:", total(pos, "quantity_sold"))
print("Daily Gold quantity:", total(daily, "units_sold"))
print("Product Gold quantity:", total(products, "units_sold"))

print("\nInventory Silver quantity change:",
      total(inventory, "quantity_change"))
print("Inventory Gold quantity change:",
      total(movements, "total_quantity_change"))

print("\nInventory Silver records:", inventory.count())
print("Inventory Gold movement count:",
      total(movements, "movement_count"))

spark.stop()