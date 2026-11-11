import subprocess
import sys

scripts = [
    "src/kenya_market_intelligence/processing/silver/kamis/kamis_silver.py",
    "src/kenya_market_intelligence/processing/silver/knbs/knbs_silver.py",
    "src/kenya_market_intelligence/processing/silver/retail/retail_silver.py",
    "src/kenya_market_intelligence/processing/gold/market_gold.py",
    "src/kenya_market_intelligence/processing/gold/retail_gold.py",
]

for script in scripts:
    print(f"\nRunning: {script}", flush=True)

    result = subprocess.run(
        ["uv", "run", "python", script]
    )

    if result.returncode != 0:
        print(f"\nFAILED: {script}")
        sys.exit(result.returncode)

print("\nAll Spark batch transformations completed successfully.")