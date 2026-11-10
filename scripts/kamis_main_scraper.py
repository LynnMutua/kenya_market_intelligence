#Discovers all commodities.
#Scrapes each commodity across multiple pages.
#Combines the records into one dataset.
#Saves the raw results to a CSV file.


import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://kamis.kilimo.go.ke/index.php/site/market"
PAGE_URL = "https://kamis.kilimo.go.ke/site/market/{}"

COLUMNS = [
    "commodity",
    "classification",
    "grade",
    "sex",
    "market",
    "wholesale",
    "retail",
    "supply_volume",
    "county",
    "date"
]

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


def get_products():
    response = session.get(BASE_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    dropdown = soup.find("select", {"name": "product"})

    if dropdown is None:
        raise RuntimeError("Product dropdown not found.")

    products = []

    for option in dropdown.find_all("option"):
        product_id = option.get("value", "").strip()
        product_name = option.get_text(" ", strip=True)

        if product_id and product_name:
            products.append((product_id, product_name))

    return products


def scrape_product(product_id, product_name):
    rows = []
    offset = 0
    page_size = 10

    while offset < 30:
        if offset == 0:
            page_url = BASE_URL
        else:
            page_url = PAGE_URL.format(offset)

        params = {
            "product": product_id,
            "per_page": str(page_size)
        }

        response = session.get(
            page_url,
            params=params,
            timeout=30
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")

        if table is None:
            print(f"  No table for {product_name}, offset {offset}")
            break

        page_rows = []

        for row in table.find_all("tr"):
            cells = row.find_all("td")

            if not cells:
                continue

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if len(values) == len(COLUMNS):
                page_rows.append(values)

        if not page_rows:
            break

        rows.extend(page_rows)

        print(
            f"  {product_name}: "
            f"{len(rows)} records collected"
        )

        # A short page means we've reached the end
        if len(page_rows) < page_size:
            break

        offset += page_size
        time.sleep(0.2)

    return rows


def main():
    products = [
    ("1", "Dry Maize"),
    ("2", "Red Sorghum"),
    ("3", "Wheat")]
    
    print(f"Discovered {len(products)} commodities.")

    all_rows = []

    for number, (product_id, product_name) in enumerate(
        products, start=1
    ):
        print(
            f"\n[{number}/{len(products)}] "
            f"Scraping {product_name}..."
        )

        try:
            rows = scrape_product(product_id, product_name)
            all_rows.extend(rows)

        except requests.RequestException as error:
            print(f"  Request failed for {product_name}: {error}")

    df = pd.DataFrame(all_rows, columns=COLUMNS)
    df.to_csv("kamis_market_raw.csv", index=False)

    print("\n--- SCRAPING SUMMARY ---")
    print("Total records:", len(df))
    print("Commodities in data:", df["commodity"].nunique())

    # Rename price columns
    df = df.rename(columns={
    "wholesale": "wholesale_price",
    "retail": "retail_price"})

    # Clean wholesale and retail prices
    for column in ["wholesale_price", "retail_price"]:
        df[column] = df[column].replace("-", pd.NA)
        df[column] = pd.to_numeric(
        df[column].str.replace("/Kg", "", regex=False), errors="coerce")
        
        print("\n--- CLEANED PRICES ---")
        print(df[["commodity", "wholesale_price", "retail_price"]].head(10))
        
        print("\n--- PRICE DATA TYPES ---")
    print(df[["wholesale_price", "retail_price"]].dtypes)

    # Clean supply volume
    df["supply_volume"] = df["supply_volume"].replace(["", "-", "N/A"],pd.NA)
    df["supply_volume"] = pd.to_numeric(df["supply_volume"],errors="coerce")

    print("\n--- CLEANED SUPPLY VOLUME ---")
    print(df[["commodity", "supply_volume"]].head(10))

    print("\n--- SUPPLY VOLUME DATA TYPE ---")
    print(df["supply_volume"].dtype)
    print("\nMissing supply volumes:", df["supply_volume"].isna().sum())

    # Standardize missing values in text columns
    text_columns = [
        "commodity",
        "classification",
        "grade",
        "sex",
        "market",
        "county",
        "date"]
    for column in text_columns:
        df[column] = df[column].replace(["", "-", "N/A"], pd.NA)

    print("\n--- MISSING VALUES AFTER CLEANING ---")
    print(df.isna().sum())

    print("\n--- CHECK GRADE AND SEX ---")
    print(df[["grade", "sex"]].head(10))

    
    # Validate the cleaned dataset
    print("\n--- DATA VALIDATION ---")
    print("Total records:", len(df))
    print("Duplicate records:", df.duplicated().sum())
    print("Unexpected commodities:", sorted(set(df["commodity"].dropna().unique())- {"Dry Maize", "Red Sorghum", "Wheat"}))
    print("Negative wholesale prices:", (df["wholesale_price"] < 0).sum())
    print("Negative retail prices:", (df["retail_price"] < 0).sum())
    print("Negative supply volumes:", (df["supply_volume"] < 0).sum())


    #output
    #print("Output file: kamis_market_raw_commodities.csv")

    # Save the cleaned dataset
    df.to_csv("kamis_market_cleaned_commodities.csv", index=False)
    print("Cleaned data saved to kamis_market_cleaned_commodities.csv")

    print("\n--- FIRST 5 RECORDS ---")
    print(df.head())

    print("\n--- DATA TYPES ---")
    print(df.dtypes)

    print("\n--- MISSING VALUES ---")
    print(df.isnull().sum())
    print(df.head(10))

    
    # Market price analysis
    print("\n--- AVERAGE PRICES BY COMMODITY ---")
    price_summary = df.groupby("commodity")[["wholesale_price", "retail_price"]].mean().round(2)
    print(price_summary)



if __name__ == "__main__":
    main()



