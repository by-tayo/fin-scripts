"""Step 7 (optional): download how national PCE and inflation moved month to month.

Run:  python 07_fetch_fred.py            (uses FRED_API_KEY from .env)
      python 07_fetch_fred.py --offline  (copies a saved snapshot instead)

Writes data/fred_trend.csv and data/us_fred_meta.json.

Unlike the other steps, this one has no "you" side - it's just the national
numbers over time, for context on whether the year you're comparing against
was a normal one.

Series used (monthly):
  PCE     Personal Consumption Expenditures, billions of dollars, seasonally
          adjusted annual rate. The same measure 01_fetch_pce.py uses annually.
  PCEPI   PCE Price Index (2017=100), seasonally adjusted. The Federal
          Reserve's preferred inflation measure. We convert it to a year-over-
          year % change, which is the number people mean by "inflation rate."
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

import pandas as pd

from pce_common import FRED_META_JSON, FRED_TREND_CSV, OFFLINE, fail, info, setting

PCE_SERIES = "PCE"
PCEPI_SERIES = "PCEPI"
API_URL = "https://api.stlouisfed.org/fred/series/observations"
MONTHS_TO_SHOW = 13  # enough for a trailing-12-month chart plus one for context


def use_offline() -> None:
    for name, dest in [("fred_trend.csv", FRED_TREND_CSV), ("us_fred_meta.json", FRED_META_JSON)]:
        src = OFFLINE / name
        if not src.exists():
            fail(f"Offline snapshot missing: {src}")
        shutil.copyfile(src, dest)
    meta = json.loads(FRED_META_JSON.read_text(encoding="utf-8"))
    info(f"Copied offline FRED snapshot (through {meta['latest_month']}) into data/")
    print("This is a saved snapshot. Get a FRED key and run without --offline for current numbers.")


def fetch_series(key: str, series_id: str, start: str) -> pd.DataFrame:
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": start,
        "sort_order": "asc",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"FRED API request for {series_id} failed ({exc.code}): {detail}\n"
             "Check: key is correct, and you are online.")
    except urllib.error.URLError as exc:
        fail(f"FRED API request for {series_id} failed: {exc}\nCheck you are online.")
    obs = body.get("observations", [])
    if not obs:
        fail(f"FRED returned no observations for {series_id}.")
    df = pd.DataFrame(obs)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                        help="use the saved snapshot instead of calling FRED")
    args = parser.parse_args()

    if args.offline:
        use_offline()
        return

    key = setting("FRED_API_KEY")
    if not key:
        fail("FRED_API_KEY is empty in .env. Sign up at "
             "https://fredaccount.stlouisfed.org/apikeys "
             "or run:  python 07_fetch_fred.py --offline")

    today = date.today()
    print("Asking FRED for monthly PCE and inflation data ...")
    pce = fetch_series(key, PCE_SERIES, str(today - timedelta(days=(MONTHS_TO_SHOW + 2) * 31)))
    info(f"{PCE_SERIES}: {len(pce)} monthly observations")
    # PCEPI needs an extra 12 months of history so we can compute year-over-year change
    # for every month we plan to show.
    pcepi = fetch_series(key, PCEPI_SERIES,
                         str(today - timedelta(days=(MONTHS_TO_SHOW + 14) * 31)))
    info(f"{PCEPI_SERIES}: {len(pcepi)} monthly observations")

    pcepi = pcepi.sort_values("date").reset_index(drop=True)
    pcepi["yoy_pct"] = pcepi["value"].pct_change(periods=12) * 100

    merged = pd.merge(
        pce.rename(columns={"value": "pce_billions"}),
        pcepi[["date", "value", "yoy_pct"]].rename(columns={"value": "pcepi_index"}),
        on="date", how="inner",
    ).dropna(subset=["yoy_pct"]).sort_values("date")

    trend = merged.tail(MONTHS_TO_SHOW).reset_index(drop=True)
    if trend.empty:
        fail("Could not line up PCE and inflation data for any month.")

    trend.to_csv(FRED_TREND_CSV, index=False, date_format="%Y-%m-%d")

    latest = trend.iloc[-1]
    meta = {
        "latest_month": latest["date"].strftime("%Y-%m"),
        "latest_pce_billions": round(float(latest["pce_billions"]), 1),
        "latest_inflation_yoy_pct": round(float(latest["yoy_pct"]), 2),
        "source": "FRED API: series PCE (monthly, billions $, SAAR) and PCEPI (monthly "
                  "price index, 2017=100, converted to year-over-year % change)",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    FRED_META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print()
    info(f"Saved {FRED_TREND_CSV.name} and {FRED_META_JSON.name}")
    print(f"     Months:                {trend['date'].min():%b %Y} to {trend['date'].max():%b %Y}")
    print(f"     Latest PCE:            ${latest['pce_billions']:,.0f} billion (annual rate)")
    print(f"     Latest inflation (YoY): {latest['yoy_pct']:.1f}%")
    print("\nCHECKPOINT: inflation should be a small number, usually 0-6%. "
          "A huge or negative number means something's off.")


if __name__ == "__main__":
    main()
