"""Step 4 (optional): download the US Consumer Expenditure Survey (CE) from the BLS API.

Run:  python 04_fetch_bls.py            (uses BLS_API_KEY from .env)
      python 04_fetch_bls.py --offline  (copies the saved 2024 snapshot instead)

Writes data/ce_benchmark.csv and data/us_ce_meta.json.

The CE survey tracks what households actually pay out of pocket, unlike PCE
(which also counts what employers and government pay on people's behalf).
That makes it a closer match for your own budget, especially for health care.

Series used (annual, "All Consumer Units", mean per consumer unit):
  CXUTOTALEXPLB0101M            Total average annual expenditures
  The 15 series listed in data/ce_categories.csv (food, housing, transport, ...)

A "consumer unit" is BLS's version of a household. CE dollar figures below are
per consumer unit, NOT per person like the PCE numbers - they are not
multiplied by HOUSEHOLD_SIZE.
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import urllib.request
from datetime import date, datetime

import pandas as pd

from pce_common import (CE_BENCHMARK_CSV, CE_META_JSON, OFFLINE, fail, info,
                        load_ce_categories, setting, warn)

TOTAL_SERIES = "CXUTOTALEXPLB0101M"
API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def use_offline() -> None:
    for name, dest in [("ce_benchmark.csv", CE_BENCHMARK_CSV), ("us_ce_meta.json", CE_META_JSON)]:
        src = OFFLINE / name
        if not src.exists():
            fail(f"Offline snapshot missing: {src}")
        shutil.copyfile(src, dest)
    meta = json.loads(CE_META_JSON.read_text(encoding="utf-8"))
    info(f"Copied offline CE snapshot for {meta['year']} into data/")
    warn("This is a saved snapshot. Get a BLS key and run without --offline for current numbers.")


def fetch_series(key: str, series_ids: list[str], years: str) -> dict:
    start_year, end_year = years.split(",")[0], years.split(",")[-1]
    payload = json.dumps({
        "seriesid": series_ids,
        "startyear": start_year,
        "endyear": end_year,
        "registrationkey": key,
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        fail(f"BLS API request failed: {exc}\n"
             "Check: key is correct, and you are online.")
    if body.get("status") != "REQUEST_SUCCEEDED":
        fail(f"BLS API returned an error: {body.get('message')}")
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                        help="use the saved snapshot instead of calling BLS")
    args = parser.parse_args()

    if args.offline:
        use_offline()
        return

    key = setting("BLS_API_KEY")
    if not key:
        fail("BLS_API_KEY is empty in .env. Sign up at "
             "https://www.bls.gov/developers/api_signature_v2.htm "
             "or run:  python 04_fetch_bls.py --offline")

    ce_cats = load_ce_categories()
    series_ids = [TOTAL_SERIES] + list(ce_cats["series_code"])

    this_year = date.today().year
    # Annual numbers for a year exist only after it ends, so stop at last year.
    years = ",".join(str(y) for y in range(this_year - 5, this_year))
    print(f"Asking BLS for annual CE data, years {years} ...")
    body = fetch_series(key, series_ids, years)

    series_list = body.get("Results", {}).get("series", [])
    by_id = {s["seriesID"]: s.get("data", []) for s in series_list}
    missing = [sid for sid in series_ids if not by_id.get(sid)]
    if missing:
        fail(f"BLS returned no data for: {missing}")

    # Newest year where every series has an annual (A01) value.
    def year_value(data_points: list[dict], year: str) -> float | None:
        for d in data_points:
            if d["year"] == year and d["period"] == "A01":
                try:
                    return float(d["value"])
                except ValueError:
                    return None
        return None

    all_years = sorted({d["year"] for d in by_id[TOTAL_SERIES]}, reverse=True)
    chosen = None
    for year in all_years:
        if all(year_value(by_id[sid], year) is not None for sid in series_ids):
            chosen = year
            break
    if chosen is None:
        fail("Could not find a year with data for every CE series.")
    info(f"Using {chosen} (newest complete year)")

    total = year_value(by_id[TOTAL_SERIES], chosen)

    rows = []
    for _, c in ce_cats.iterrows():
        value = year_value(by_id[c["series_code"]], chosen)
        rows.append({"ce_key": c["ce_key"], "series_code": c["series_code"], "value": value})
    bench = pd.DataFrame(rows)

    # Sanity check so a bad fetch is caught right away.
    leaf_sum = bench["value"].sum()
    if not 0.95 < leaf_sum / total < 1.05:
        warn(f"The categories add to ${leaf_sum:,.0f} vs total ${total:,.0f} "
             "(expected close to 100%). Check the data before trusting results.")

    bench.to_csv(CE_BENCHMARK_CSV, index=False)
    meta = {
        "year": int(chosen),
        "total_annual_expenditure": round(total, 2),
        "source": "BLS API: Consumer Expenditure Survey, All Consumer Units, mean annual "
                  "expenditure per consumer unit (series CXU...LB0101M)",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    CE_META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print()
    info(f"Saved {CE_BENCHMARK_CSV.name} and {CE_META_JSON.name}")
    print(f"     Year:                          {chosen}")
    print(f"     Average annual expenditure:    ${total:,.0f} per consumer unit")
    print("\nCHECKPOINT: total should be around $75,000-80,000 per consumer unit. "
          "Much bigger or smaller means something went wrong.")


if __name__ == "__main__":
    main()
