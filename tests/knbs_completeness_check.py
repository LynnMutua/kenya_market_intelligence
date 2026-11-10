
from pathlib import Path
from collections import Counter
import re
import calendar
import csv
from datetime import date


PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_DIR / "data" / "bronze" / "knbs" / "cpi_pdfs"
OUTPUT = PROJECT_DIR / "data" / "bronze" / "knbs" / "knbs_completeness.csv"

#five-year window: November 2021 to October 2026
MONTHS = list(calendar.month_name)[1:]

start = date(2023, 4, 1)
end = date(2026, 9, 1)
expected = []
year, month = start.year, start.month

while (year, month) <= (end.year, end.month):
    expected.append((year, calendar.month_name[month]))

    month += 1
    if month > 12:
        month = 1
        year += 1


#month and year in each PDF filename
pattern = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\b.*?\b(20\d{2})\b"
    r"|\b(20\d{2})\b.*?\b(" + "|".join(MONTHS) + r")\b",
    re.IGNORECASE,
)

found = Counter()

for pdf in PDF_DIR.glob("*.pdf"):
    match = re.search(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)[\s_-]+(20\d{2})",
        pdf.name,
        re.IGNORECASE,
    )

    if match:
        month = match.group(1).capitalize()
        year = int(match.group(2))
        found[(year, month)] += 1

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=["year", "month", "status", "file_count"]
    )
    writer.writeheader()

    for year, month in expected:
        count = found[(year, month)]

        if count == 0:
            status = "MISSING"
        elif count > 1:
            status = "DUPLICATE"
        else:
            status = "PRESENT"

        writer.writerow({
            "year": year,
            "month": month,
            "status": status,
            "file_count": count,
        })

print(f"Expected months: {len(expected)}")
print(f"Present: {sum(found[m] >= 1 for m in expected)}")
print(f"Missing: {sum(found[m] == 0 for m in expected)}")
print(f"Duplicates: {sum(found[m] > 1 for m in expected)}")
print(f"Report saved to: {OUTPUT}")
