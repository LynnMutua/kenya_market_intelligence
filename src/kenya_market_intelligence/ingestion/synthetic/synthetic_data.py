
import csv
import random
import calendar
from pathlib import Path
from datetime import date, datetime, timedelta

random.seed(42)

OUTPUT_DIR = Path("data/synthetic")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = date(2025, 11, 1)
END_DATE = date(2026, 10, 31)

TARGET_SALES_LINES = 250_000
ANOMALY_RATE = 0.005

def save_csv(filename, records):
    #save a list of dictionaries to CSV
    if not records:
        print(f"No records generated for {filename}")
        return

    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"Created {filepath}: {len(records):,} records")

#generate a random date within the historical period
def random_date():
    total_days = (END_DATE - START_DATE).days
    return START_DATE + timedelta(
        days=random.randint(0, total_days))

#generate a random retail transaction timestamp
def random_datetime():
    selected_date = random_date()
    hour = random.randint(7, 21)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

#stores
locations = [ ("Nairobi", "Nairobi"), ("Mombasa", "Coast"), ("Kisumu", "Nyanza"), ("Nakuru", "Rift Valley"), ("Eldoret", "Rift Valley"), ("Nyeri", "Central"), ("Meru", "Eastern"), ("Kakamega", "Western"), ("Machakos", "Eastern"),
    ("Garissa", "North Eastern"), ("Kiambu", "Central"), ("Kilifi", "Coast"), ("Kajiado", "Rift Valley"), ("Nanyuki", "Rift Valley"), ("Bungoma", "Western"),("Busia", "Western"), ("Embu", "Eastern"),
    ("Kitui", "Eastern"), ("Kericho", "Rift Valley"), ("Narok", "Rift Valley"), ("Nyandarua", "Central"), ("Murang'a", "Central"), ("Migori", "Nyanza"), ("Chuka", "Eastern"), ("Voi", "Coast")]

stores = []
for index, (town, region) in enumerate(locations, start=1):
    stores.append({
        "store_id": f"STR-{index:03d}",
        "store_name": f"MegaStore {town}",
        "county": town, "town": town, "region": region})
save_csv("stores.csv", stores)

#suppliers
supplier_locations = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Kiambu", "Machakos", "Meru", "Eldoret", "Kakamega", "Nyeri"]
suppliers = []
for index in range(1, 21):
    county = random.choice(supplier_locations)
    suppliers.append({"supplier_id": f"SUP-{index:03d}", "supplier_name": f"Kenya Supplier {index:03d}", "county": county, "contact_email": f"sales{index}@supplier{index}.co.ke"})
save_csv("suppliers.csv", suppliers)

#products
product_templates = [
    ("Maize", "Grains", "Kg", 65), ("Maize Flour", "Cereals", "2Kg Pack", 180), ("Rice", "Grains", "Kg", 160), ("Beans", "Legumes", "Kg", 140),
    ("Green Grams", "Legumes", "Kg", 180), ("Wheat Flour", "Cereals", "2Kg Pack", 170), ("Potatoes", "Vegetables", "Kg", 60), ("Sweet Potatoes", "Vegetables", "Kg", 75), ("Tomatoes", "Vegetables", "Kg", 100),
    ("Onions", "Vegetables", "Kg", 90), ("Cabbage", "Vegetables", "Piece", 80), ("Carrots", "Vegetables", "Kg", 85), ("Bananas", "Fruits", "Kg", 100), ("Avocado", "Fruits", "Piece", 30),
    ("Mangoes", "Fruits", "Piece", 40), ("Cooking Oil", "Household", "Litre", 300), ("Sugar", "Household", "Kg", 180), ("Salt", "Household", "Kg", 40), ("Milk", "Dairy", "Litre", 70),
    ("Eggs", "Dairy", "Tray", 450)]

brands = ["FreshChoice", "WantamFresh", "ValueMart", "Kenya moja", "Daily needs", "Premium best", "KerriGold", "HomeQwetu", "NatureFresh", "Sokoni Plus"]

products = []
product_commodity_map = []
product_id = 1

for template in product_templates:
    product_name, category, unit, base_price = template
    for brand in brands:
        products.append({
            "product_id": f"PRD-{product_id:04d}", "product_name": product_name,
            "category": category, "brand": brand, "unit_of_measure": unit,
            "base_price": base_price})

        product_commodity_map.append({"product_id": f"PRD-{product_id:04d}", "commodity": product_name, "classification": category})
        product_id += 1

save_csv("products.csv", products)
save_csv("product_commodity_map.csv", product_commodity_map)

# Supplier-product map
product_supplier_map = []
for product in products:
    #a product is supplied by 2 to 4 suppliers
    selected_suppliers = random.sample(suppliers, random.randint(2, 4))

    for supplier in selected_suppliers:
        product_supplier_map.append({"product_id": product["product_id"], "supplier_id": supplier["supplier_id"]})

save_csv("product_supplier_map.csv", product_supplier_map)

# Create a lookup: product_id -> available suppliers
suppliers_by_product = {}
for mapping in product_supplier_map:
    suppliers_by_product.setdefault(mapping["product_id"], []).append(mapping["supplier_id"])

#the market
commodity_price_ranges = {
    "Maize": (35, 75), "Maize Flour": (100, 200), "Rice": (100, 220), "Beans": (90, 190), "Green Grams": (100, 220),"Wheat Flour": (100, 200), "Potatoes": (30, 100), "Sweet Potatoes": (35, 110), "Tomatoes": (40, 150), "Onions": (40, 140), "Cabbage": (30, 100),
    "Carrots": (40, 120), "Bananas": (40, 130), "Avocado": (10, 60), "Mangoes": (15, 80), "Cooking Oil": (200, 400), "Sugar": (130, 220), "Salt": (20, 60), "Milk": (50, 100), "Eggs": (300, 550)}


def generate_market_observations():
    observations = []
    #one observation per commodity, store and month
    commodities = {}
    for mapping in product_commodity_map:
        commodities[mapping["commodity"]] = mapping["classification"]
    current_month = date( START_DATE.year, START_DATE.month, 1)

    while current_month <= END_DATE:
        days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]

        for store in stores:
            for commodity, classification in commodities.items():
                low_price, high_price = commodity_price_ranges[commodity]
                base_price = random.uniform( low_price, high_price)
                wholesale_price = round(base_price, 2)
                retail_price = round(wholesale_price * random.uniform(1.08, 1.25), 2)
                supply_volume = round(random.uniform(500, 20000),2)
                observation_date = date(current_month.year, current_month.month, random.randint(1, days_in_month))
                observations.append({
                    "commodity": commodity, "classification": classification,"grade": "Standard", "sex": "",
                    "market": f"{store['town']} Market", "wholesale_price": wholesale_price, "retail_price": retail_price, "supply_volume": supply_volume,
                    "county": store["county"], "date": observation_date.isoformat(),"record_source": "synthetic"})

        #next month
        if current_month.month == 12:
            current_month = date(current_month.year + 1, 1, 1)
        else:
            current_month = date(current_month.year, current_month.month + 1, 1)
    return observations

market_observations = generate_market_observations()
save_csv("synthetic_market_observations.csv", market_observations)

#pos sales generation
def generate_sales_dates():

    while True:
        selected_date = random_date()
        weekday_weight = (1.25 if selected_date.weekday() >= 5 else 1.0)

        seasonal_weight = (1.30 if selected_date.month == 12 else 1.0)

        probability = min(0.95, 0.65 * weekday_weight * seasonal_weight)

        if random.random() < probability:
            return selected_date

def generate_pos_sales():
    sales = []
    transaction_number = 1
    line_number = 1
    print("\nGenerating POS sales transactions...")

    while len(sales) < TARGET_SALES_LINES:
        transaction_id = f"TXN-{transaction_number:07d}"
        transaction_date = generate_sales_dates()
        transaction_time = datetime(transaction_date.year, transaction_date.month, transaction_date.day,
            random.randint(7, 21), random.randint(0, 59), random.randint(0, 59))
        store = random.choice(stores)

        #a transaction contains between one and five items
        number_of_items = random.randint(1, 5)
        for _ in range(number_of_items):
            if len(sales) >= TARGET_SALES_LINES:
                break
            product = random.choice(products)
            available_supplier_ids = suppliers_by_product[product["product_id"]]
            supplier = random.choice(available_supplier_ids)
            quantity = random.choices(
                [1, 2, 3, 4, 5, 6, 10],
                weights=[35, 25, 15, 10, 8, 5, 2])[0]

            base_price = float(product["base_price"])
            unit_price = round(base_price * random.uniform(0.95, 1.10), 2)

            total_amount = round(quantity * unit_price, 2)

            sales.append({
                "transaction_line_id": f"LINE-{line_number:08d}",
                "transaction_id": transaction_id,
                "transaction_datetime": transaction_time.strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": store["store_id"],
                "product_id": product["product_id"],
                "supplier_id": supplier,
                "quantity_sold": quantity,
                "unit_price": unit_price,
                "total_amount": total_amount,
                "payment_method": random.choice(["Cash", "M-Pesa", "Card"])})
            line_number += 1
        transaction_number += 1
    return sales


#anomalies
def inject_sales_anomalies(sales):
    sales = [record.copy() for record in sales]
    anomaly_count = round(
        len(sales) * ANOMALY_RATE)

    selected_indices = random.sample(
        range(len(sales)),
        anomaly_count)

    anomaly_types = ["duplicate_record", "missing_product_id", "missing_supplier_id", "negative_quantity", "negative_unit_price", "invalid_date"]

    audit = []
    for position, index in enumerate(selected_indices):
        record = sales[index]
        anomaly_type = anomaly_types[position % len(anomaly_types)]
        record_id = record["transaction_line_id"]

        if anomaly_type == "duplicate_record":
            duplicate = record.copy()
            sales.append(duplicate)
            audit.append({"dataset": "pos_sales", "record_id": record_id, "anomaly_type": anomaly_type, "field": "transaction_line_id", "original_value": record_id, "injected_value": record_id})

        else:
            field_map = {
                "missing_product_id": "product_id",
                "missing_supplier_id": "supplier_id",
                "negative_quantity": "quantity_sold",
                "negative_unit_price": "unit_price",
                "invalid_date": "transaction_datetime"}

            field = field_map[anomaly_type]
            original_value = record[field]
            if anomaly_type in [
                "missing_product_id",
                "missing_supplier_id"]:
                injected_value = ""

            elif anomaly_type == "negative_quantity":
                injected_value = -abs(int(original_value))

            elif anomaly_type == "negative_unit_price":
                injected_value = -abs(
                    float(original_value))

            else:
                injected_value = "invalid-date"
            record[field] = injected_value

            audit.append({
                "dataset": "pos_sales",
                "record_id": record_id,
                "anomaly_type": anomaly_type,
                "field": field,
                "original_value": original_value,
                "injected_value": injected_value})

    return sales, audit

#pos generator
clean_sales = generate_pos_sales()
sales_with_anomalies, sales_audit = inject_sales_anomalies(clean_sales)

save_csv("synthetic_pos_transactions.csv", sales_with_anomalies)
save_csv("synthetic_data_anomaly_audit.csv", sales_audit)


#summary 
print("\n======================================")
print("SYNTHETIC DATA GENERATION SUMMARY")
print("======================================")

print(f"Stores: {len(stores):,}")
print(f"Suppliers: {len(suppliers):,}")
print(f"Products: {len(products):,}")
print(f"Product mappings: {len(product_commodity_map):,}")
print(f"Market observations: {len(market_observations):,}")
print(f"Product-supplier mappings: {len(product_supplier_map):,}")
print(f"Clean POS sales lines: {len(clean_sales):,}")
print(f"Final POS sales lines: {len(sales_with_anomalies):,}")
print(f"Injected anomalies: {len(sales_audit):,}")

print(f"\nHistorical period: {START_DATE} to {END_DATE}")
print(f"Output directory: {OUTPUT_DIR}")

print("\nSynthetic data generation complete.")

# inventory movement
def generate_inventory_movements():
    totals = {}
    adjustments = {}
    recorded = set()
    movement_id = 1

    #monthly sales per store and product
    for sale in clean_sales:
        year_month = sale["transaction_datetime"][:7]
        key = (sale["store_id"], sale["product_id"], year_month)
        totals[key] = totals.get(key, 0) + int(sale["quantity_sold"])

    for key in totals:
        if random.random() < 0.05:
            adjustment_type = random.choice([
                "damaged_goods", "stock_count_correction"])
            quantity = random.randint(1, 3)

            if adjustment_type == "damaged_goods":
                quantity = -quantity
            else:
                quantity *= random.choice([-1, 1])

            adjustments[key] = (adjustment_type, quantity)

    print("Adjustments generated:", len(adjustments))
    print("Adjustment types:", {
        value[0] for value in adjustments.values()})

    #sort sales
    sorted_sales = sorted(clean_sales, key=lambda x: x["transaction_datetime"])

    #inventory movements to CSV
    filename = OUTPUT_DIR / "synthetic_inventory_movements.csv"
    with open(filename, "w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "movement_id", "movement_datetime", "store_id",
            "product_id", "supplier_id", "movement_type",
            "quantity_change", "reference_id"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for sale in sorted_sales:
            dt_str = sale["transaction_datetime"]
            year_month = dt_str[:7]
            date_part = dt_str[:10]
            key = (sale["store_id"], sale["product_id"], year_month)
            # one receipt per store, product and month
            if key not in recorded:
                supplier = random.choice(suppliers_by_product[sale["product_id"]])
                adjustment = adjustments.get(key, ("", 0))[1]
                writer.writerow({
                    "movement_id": f"INV-{movement_id:08d}", "movement_datetime": f"{date_part} 06:00:00", "store_id": sale["store_id"], "product_id": sale["product_id"],
                    "supplier_id": supplier, "movement_type": "stock_receipt", "quantity_change": totals[key] - adjustment + 20, "reference_id": f"REC-{movement_id:07d}"})
                movement_id += 1
                recorded.add(key)

                if key in adjustments:
                    adjustment_type, quantity = adjustments[key]
                    writer.writerow({
                        "movement_id": f"INV-{movement_id:08d}", "movement_datetime": f"{date_part} 07:00:00", "store_id": sale["store_id"], "product_id": sale["product_id"], "supplier_id": "",
                        "movement_type": adjustment_type, "quantity_change": quantity, "reference_id": f"ADJ-{movement_id:07d}"})
                    movement_id += 1
                    
            #stock deduction for each sale
            writer.writerow({
                "movement_id": f"INV-{movement_id:08d}", "movement_datetime": dt_str,
                "store_id": sale["store_id"], "product_id": sale["product_id"], "supplier_id": "",
                "movement_type": "stock_sale", "quantity_change": -int(sale["quantity_sold"]), "reference_id": sale["transaction_line_id"]})
            movement_id += 1

    return movement_id - 1


inventory_count = generate_inventory_movements()
print(f"Inventory movements: {inventory_count:,}")