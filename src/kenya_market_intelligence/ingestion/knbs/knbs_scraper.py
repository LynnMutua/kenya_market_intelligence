
from pathlib import Path
from datetime import date
import calendar
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_DIR = Path(__file__).resolve().parent.parent
SAVE_DIR = PROJECT_DIR / "data" / "bronze" / "knbs" / "cpi_pdfs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://repository.knbs.or.ke/server/api/discover/search/objects"
BASE_URL = "https://repository.knbs.or.ke/server/api"
HEADERS = {"User-Agent": "KenyaMarketIntelligence/1.0"}
TIMEOUT = 30



def discover_pdf_links():
    #search KNBS for monthly CPI reports from November 2021 to October 2026
    jobs = {}
    current = date(2021, 11, 1)
    end = date(2026, 9, 1)

    while current <= end:
        month_name = calendar.month_name[current.month]
        year = current.year
        print(f"Searching: {month_name} {year}")

        page = 0
        total_pages = 1

        while page < total_pages:
            try:
                response = requests.get(
                    API_URL,
                    params={
                        "query": f'"{month_name} {year}"',
                        "dsoType": "item",
                        "page": page,
                        "size": 100,
                    },
                    headers=HEADERS,
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()

                search_result = data.get("_embedded", {}).get(
                    "searchResult", {}
                )
                results = search_result.get("_embedded", {}).get(
                    "objects", []
                )

                page_info = search_result.get("page", {})
                total_pages = page_info.get("totalPages", 1)

                for result in results:
                    item = result.get("_embedded", {}).get(
                        "indexableObject", {}
                    )
                    title = item.get("name", "")
                    lower_title = title.lower()

                    if (
                        month_name.lower() not in lower_title
                        or str(year) not in title
                        or not any(
                            term in lower_title
                            for term in (
                                "cpi",
                                "inflation",
                                "consumer price",
                            )
                        )
                    ):
                        continue

                    item_uuid = item.get("uuid")
                    if not item_uuid:
                        continue

                    item_url = f"{BASE_URL}/core/items/{item_uuid}"
                    item_response = requests.get(
                        item_url, headers=HEADERS, timeout=TIMEOUT
                    )
                    item_response.raise_for_status()

                    bundles_url = (
                        item_response.json()
                        .get("_links", {})
                        .get("bundles", {})
                        .get("href")
                    )
                    if not bundles_url:
                        continue

                    bundle_response = requests.get(
                        bundles_url, headers=HEADERS, timeout=TIMEOUT
                    )
                    bundle_response.raise_for_status()

                    bundles = bundle_response.json().get(
                        "_embedded", {}
                    ).get("bundles", [])

                    for bundle in bundles:
                        if bundle.get("name") != "ORIGINAL":
                            continue

                        bits_url = (
                            bundle.get("_links", {})
                            .get("bitstreams", {})
                            .get("href")
                        )
                        if not bits_url:
                            continue

                        bits_response = requests.get(
                            bits_url, headers=HEADERS, timeout=TIMEOUT
                        )
                        bits_response.raise_for_status()

                        bitstreams = bits_response.json().get(
                            "_embedded", {}
                        ).get("bitstreams", [])

                        for bit in bitstreams:
                            if not bit.get("name", "").lower().endswith(
                                ".pdf"
                            ):
                                continue

                            content_url = (
                                bit.get("_links", {})
                                .get("content", {})
                                .get("href")
                            )
                            if not content_url:
                                continue

                            month_key = (year, current.month)
                            filename = (
                                "Kenya-Consumer-Price-Indices-and-"
                                f"Inflation-Rates-{month_name}-{year}.pdf"
                            )

                            if month_key not in jobs:
                                jobs[month_key] = {
                                    "url": content_url,
                                    "filename": filename,
                                }

                page += 1
                time.sleep(0.2)

            except requests.RequestException as exc:
                print(
                    f"[FAILED] {month_name} {year}, page {page}: {exc}"
                )
                break

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    print(f"Discovered {len(jobs)} monthly PDF links.")
    return list(jobs.values())



def download_one_file(job):
    destination = SAVE_DIR / job["filename"]

    if destination.exists() and destination.stat().st_size > 0:
        return f"[SKIP] {destination.name}"

    try:
        with requests.get(
            job["url"],
            headers=HEADERS,
            timeout=TIMEOUT,
            stream=True,
        ) as response:
            response.raise_for_status()

            first_chunk = next(response.iter_content(8192), b"")
            content_type = response.headers.get("Content-Type", "").lower()

            if not (
                first_chunk.startswith(b"%PDF-")
                or "application/pdf" in content_type
            ):
                return f"[FAILED] Not a PDF: {job['filename']}"

            with destination.open("wb") as file:
                file.write(first_chunk)
                for chunk in response.iter_content(8192):
                    if chunk:
                        file.write(chunk)

        return f"[SUCCESS] {destination.name}"

    except requests.RequestException as exc:
        return f"[FAILED] {job['filename']}: {exc}"


def main():
    print("Discovering KNBS CPI reports...")
    jobs = discover_pdf_links()
    print(f"Found {len(jobs)} PDF links.")

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(download_one_file, job) for job in jobs]
        for future in as_completed(futures):
            print(future.result())

    print(f"Finished. Files are stored in: {SAVE_DIR}")


if __name__ == "__main__":
    main()

