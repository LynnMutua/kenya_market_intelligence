
from pathlib import Path
import re
import pdfplumber
import pandas as pd

# --------------------------------------------------
# PATHS AND SETTINGS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

BRONZE_DIR = PROJECT_DIR / "data/bronze/knbs/cpi_pdfs"
SILVER_DIR = PROJECT_DIR / "data/silver/knbs"

SILVER_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = pd.Timestamp("2023-04-01")
END_DATE = pd.Timestamp("2026-09-30")

MONTHS = {
    month.lower(): number
    for number, month in enumerate(
        [
            "", "January", "February", "March", "April",
            "May", "June", "July", "August", "September",
            "October", "November", "December"
        ]
    )if month}

DIVISIONS = [
    "Food and Non-Alcoholic Beverages",
    "Alcoholic Beverages, Tobacco and Narcotics",
    "Clothing and Footwear",
    "Housing, Water, Electricity, Gas and Other Fuels",
    "Furnishings, Household Equipment and Routine Household Maintenance",
    "Health",
    "Transport",
    "Information and Communication",
    "Recreation, Sport and Culture",
    "Education Services",
    "Restaurants and Accommodation Services",
    "Insurance and Financial Services",
    "Personal Care, Social Protection and Miscellaneous Goods and Services",
    "Total"]

def get_report_date(filename):
    name = Path(filename).stem.lower()

    match = re.search(
        r"(january|february|march|april|may|june|july|"
        r"august|september|october|november|december)"
        r"[-_\s]+(20\d{2})",
        name)

    if match:
        month = MONTHS[match.group(1)]
        year = int(match.group(2))
        return pd.Timestamp(year, month, 1)

    return None


def clean_number(value):
    if value is None:
        return None

    value = str(value).replace(",", "").replace(" ", "").strip()

    try:
        return float(value)
    except ValueError:
        return None


#CPI BY EXPENDITURE DIVISION
def extract_cpi_divisions(pdf, report_date):
    text = ""

    for page in pdf.pages:
        page_text = page.extract_text() or ""
        if "13 COICOP Divisions" in page_text:
            text = page_text
            break

    if not text:
        return []

    #normalise line breaks and repeated spaces.
    text = re.sub(r"\s+", " ", text)

    records = []

    for division in sorted(DIVISIONS, key=len, reverse=True):
        normalised_division = re.sub(r"\s+", r"\\s+", division)

        pattern = (
            re.escape(division).replace(r"\ ", r"\s+")
            + r"\s+([\d,]+\.\d+)\s+"
            + r"(-?[\d.]+)\s+"
            + r"(-?[\d.]+)")

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            records.append({
                "date": report_date,
                "division": division,
                "weight_percent": clean_number(match.group(1)),
                "monthly_change_percent": clean_number(match.group(2)),
                "annual_change_percent": clean_number(match.group(3))})

    return records


#save retail prices

def extract_commodity_prices(pdf, report_date):
    import re

    # Skip scanned reports with unreliable text extraction
    if report_date.strftime("%Y-%m") in ("2023-09", "2023-10"):
        print(f"Skipping {report_date:%Y-%m} commodity prices.")
        return []

    #if pdf.name == "Kenya-Consumer-Price-Indices-and-Inflation-Rates-May-2024.pdf":
        print(f"Skipping highlights-only PDF: {pdf.name}")
        return []

    number = r"(?:\(?-?\d[\d,]*(?:\.\d+)?\)?|-)"

    row_pattern = re.compile(
    rf"^(.+?)\s+(\d+)\s*([A-Za-z][A-Za-z /-]*?)\s+"
    rf"({number})\s+({number})\s+({number})\s+"
    rf"({number})\s+((?:{number})|(?:\d\s+\d{{1,2}}\.\d+))$")

    def parse_value(value):
        value = value.strip()
        if value == "-":
            return None

        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]
        return clean_number(value)

    def parse_percent(value):
        value = value.strip()
    # Join split annual percentages: 1 0.3 -> 10.3
        value = re.sub(
            r"(\d)\s+(\d{1,2}\.\d+)",
            r"\1\2",
            value)

        return parse_value(value)


    
    def repair_line(line):
        # Repair split decimal points: 2 .7 -> 2.7
        line = re.sub(r"(\d)\s+\.\s*(\d)", r"\1.\2", line)

        # Repair split commas: 1 ,274.06 -> 1,274.06
        line = re.sub(r"(\d)\s+,\s*(\d)", r"\1,\2", line)

        # Repair split numeric values: 3 26.36 -> 326.36
        line = re.sub(
            r"(?<![\d,])(\d)\s+(\d{1,2}\.\d{2})",
            r"\1\2",
            line)

        return line


    lines = []

    for page in pdf.pages:
        page_text = page.extract_text() or ""
        lines.extend(page_text.splitlines())

    records = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Join commodity names that continue on the next line.
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()

            is_wrapped_fresh_cream = ("Fresh unpacketed cow milk / Fresh" in line
                and next_line.startswith("Cream "))

            is_wrapped_bus_fare = ("Country Bus /Matatu Fare" in line and not re.search(r"\d+\s*[A-Za-z]", line))

            if is_wrapped_fresh_cream or is_wrapped_bus_fare:
                line += " " + next_line
                i += 1

        line = repair_line(line)
        match = row_pattern.match(line)

        if not match and report_date.strftime("%Y-%m") == "2023-12":
            if re.search(r"Mangoes|Sugar|Beef|Mutton|Carrots|Kerosene|Electricity|Petrol|Diesel|Country Bus", line, re.IGNORECASE):
                print("UNMATCHED:", repr(line))

        if match:
            records.append({
                "date": report_date,
                "commodity": match.group(1).strip(),
                "quantity": parse_value(match.group(2)),
                "unit": match.group(3).strip(),
                "price_previous_year": parse_value(match.group(4)),
                "price_previous_month": parse_value(match.group(5)),
                "price_current_month": parse_value(match.group(6)),
                "monthly_change_percent": parse_value(match.group(7)),
                "annual_change_percent": parse_percent(match.group(8)),
            })

        i += 1

    return records



#bronze to silver
def main():

    division_records = []
    commodity_records = []
    failed_reports = []

    pdf_files = sorted(
        [
            p for p in BRONZE_DIR.glob("*.pdf")
            if "highlights" not in p.name.lower()
            and "kenya-consumer-price-indices-and-inflation-rates-may-2024"
            not in p.name.lower()
        ]
    )

    print(f"PDF files found in Bronze: {len(pdf_files)}")

    for pdf_file in pdf_files:
        report_date = get_report_date(pdf_file.name)

        if report_date is None:
            print(f"[SKIP] Could not identify date: {pdf_file.name}")
            continue

        if not START_DATE <= report_date <= END_DATE:
            continue

        print(f"Processing: {pdf_file.name}")

        try:
            with pdfplumber.open(pdf_file) as pdf:

                divisions = extract_cpi_divisions(pdf, report_date)
                commodities = extract_commodity_prices(pdf, report_date)

                division_records.extend(divisions)
                commodity_records.extend(commodities)

                if not divisions or not commodities:
                    failed_reports.append({
                        "file": pdf_file.name,
                        "division_records": len(divisions),
                        "commodity_records": len(commodities),
                        "issue": "One or both tables returned no records"
                    })

        except Exception as error:
            failed_reports.append({
                "file": pdf_file.name,
                "division_records": 0,
                "commodity_records": 0,
                "issue": str(error)
            })

    # Create DataFrames
    divisions_df = pd.DataFrame(division_records)
    commodities_df = pd.DataFrame(commodity_records)

    # Clean and deduplicate CPI divisions
    if not divisions_df.empty:
        divisions_df["date"] = pd.to_datetime(
            divisions_df["date"], errors="coerce"
        )
        divisions_df = divisions_df.drop_duplicates(
            subset=["date", "division"]
        )
        divisions_df = divisions_df.sort_values(
            ["date", "division"]
        ).reset_index(drop=True)

    # Clean and deduplicate commodity prices
    if not commodities_df.empty:
        commodities_df["date"] = pd.to_datetime(
            commodities_df["date"], errors="coerce"
        )
        commodities_df = commodities_df.drop_duplicates(
            subset=["date", "commodity"]
        )
        commodities_df = commodities_df.sort_values(
            ["date", "commodity"]
        ).reset_index(drop=True)

    # Save Silver datasets
    divisions_df.to_csv(
        SILVER_DIR / "knbs_cpi_divisions.csv", index=False
    )
    commodities_df.to_csv(
        SILVER_DIR / "knbs_commodity_prices.csv", index=False
    )
    pd.DataFrame(failed_reports).to_csv(
        SILVER_DIR / "knbs_extraction_issues.csv", index=False
    )

    # Transformation summary
    print("\n========== KNBS SILVER SUMMARY ==========")

    print("CPI division records:", len(divisions_df))
    print("Commodity price records:", len(commodities_df))

    if not divisions_df.empty:
        print(
            "CPI date range:",
            divisions_df["date"].min(),
            "to",
            divisions_df["date"].max()
        )

    if not commodities_df.empty:
        print(
            "Commodity date range:",
            commodities_df["date"].min(),
            "to",
            commodities_df["date"].max()
        )

    print("Reports with extraction issues:", len(failed_reports))
    print("Silver output:", SILVER_DIR)


if __name__ == "__main__":
    main()