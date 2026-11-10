
import pandas as pd

# Load cleaned KAMIS data
file_path = "data/silver/kamis/kamis_market_cleaned_commodities.csv"
df = pd.read_csv(file_path)

#check for duplicate rows
duplicates = df[df.duplicated()]

print("KAMIS DUPLICATE CHECK")
print("---------------------")
print(f"Total records: {len(df)}")
print(f"Duplicate records: {len(duplicates)}")

if duplicates.empty:
    print("No duplicate records found.")
else:
    print("\nDuplicate records:")
    print(duplicates)

    #save duplicates for inspection
    duplicates.to_csv(
        "data/silver/kamis/kamis_duplicates.csv",
        index=False
    )
    print("\nDuplicates saved to data/silver/kamis/kamis_duplicates.csv")
