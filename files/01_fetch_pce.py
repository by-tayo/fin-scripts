"""Step 1: download US Personal Consumption Expenditures (PCE) from the BEA API.

Run:  python 01_fetch_pce.py            (uses BEA_API_KEY from .env)
      python 01_fetch_pce.py --offline  (copies the saved 2025 snapshot instead)

Writes data/pce_benchmark.csv and data/us_meta.json.

BEA tables used (annual):
  T20305  Table 2.3.5  PCE by Major Type of Product   -> 15 spending categories + total
  T70100  Table 7.1    Per capita series              -> PCE per person (series A794RC)
  T20100  Table 2.1    Personal Income and Its Disposition -> saving rate (series A072RC)
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date, datetime

import pandas as pd

from pce_common import (BENCHMARK_CSV, META_JSON, OFFLINE, fail, info,
                        load_categories, setting, warn)

PER_CAPITA_CODE = "A794RC"
SAVING_RATE_CODE = "A072RC"


def use_offline() -> None:
    for name, dest in [("pce_benchmark.csv", BENCHMARK_CSV), ("us_meta.json", META_JSON)]:
        src = OFFLINE / name
        if not src.exists():
            fail(f"Offline snapshot missing: {src}")
        shutil.copyfile(src, dest)
    meta = json.loads(META_JSON.read_text(encoding="utf-8"))
    info(f"Copied offline snapshot for {meta['year']} into data/")
    warn("This is a saved snapshot. Get a BEA key and run without --offline for current numbers.")


def fetch_table(key: str, table: str, years: str) -> pd.DataFrame:
    import beaapi

    try:
        df = beaapi.get_data(key, datasetname="NIPA", TableName=table,
                             Frequency="A", Year=years)
    except Exception as exc:  # beaapi raises several error types
        fail(f"BEA API request for {table} failed: {exc}\n"
             "Check: key is correct and activated (click the link in BEA's email), "
             "and you are online.")
    if df is None or len(df) == 0:
        fail(f"BEA returned no rows for {table}.")
    needed = {"SeriesCode", "TimePeriod", "DataValue"}
    missing = needed - set(df.columns)
    if missing:
        fail(f"BEA response for {table} is missing columns {missing}. "
             f"Columns received: {list(df.columns)}")
    df = df.copy()
    # Make values numeric no matter how they arrived ("1,234.5", "(NA)", ...).
    df["value"] = pd.to_numeric(
        df["DataValue"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    if "UNIT_MULT" in df.columns:
        df["unit_mult"] = pd.to_numeric(df["UNIT_MULT"], errors="coerce").fillna(0).astype(int)
    else:
        df["unit_mult"] = 0
    df["year"] = df["TimePeriod"].astype(str).str[:4].astype(int)
    df["SeriesCode"] = df["SeriesCode"].astype(str).str.strip()
    return df


def pick(df: pd.DataFrame, code: str, year: int) -> tuple[float, int] | None:
    rows = df[(df["SeriesCode"] == code) & (df["year"] == year)].dropna(subset=["value"])
    if rows.empty:
        return None
    row = rows.iloc[0]
    return float(row["value"]), int(row["unit_mult"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                        help="use the saved snapshot instead of calling BEA")
    args = parser.parse_args()

    if args.offline:
        use_offline()
        return

    key = setting("BEA_API_KEY")
    if not key or key.lower().startswith("paste"):
        fail("BEA_API_KEY is empty in .env. Sign up at https://apps.bea.gov/api/signup/ "
             "or run:  python 01_fetch_pce.py --offline")

    this_year = date.today().year
    # Annual numbers for a year exist only after it ends, so stop at last year.
    years = ",".join(str(y) for y in range(this_year - 4, this_year))
    print(f"Asking BEA for annual data, years {years} ...")

    cats = load_categories()
    t235 = fetch_table(key, "T20305", years)
    info(f"T20305: {len(t235)} rows")
    t71 = fetch_table(key, "T70100", years)
    info(f"T70100: {len(t71)} rows")
    t21 = fetch_table(key, "T20100", years)
    info(f"T20100: {len(t21)} rows")

    # Total PCE is line 1 of Table 2.3.5.
    if "LineNumber" not in t235.columns:
        fail("T20305 has no LineNumber column; cannot find total PCE.")
    t235["LineNumber"] = pd.to_numeric(t235["LineNumber"], errors="coerce")
    total_rows = t235[t235["LineNumber"] == 1]

    # Newest year where every piece exists.
    chosen = None
    for year in sorted(t235["year"].unique(), reverse=True):
        have_cats = all(pick(t235, c, year) for c in cats["series_code"])
        have_total = not total_rows[(total_rows["year"] == year)].dropna(subset=["value"]).empty
        have_pc = pick(t71, PER_CAPITA_CODE, year) is not None
        if have_cats and have_total and have_pc:
            chosen = int(year)
            break
    if chosen is None:
        found = sorted(t235["SeriesCode"].unique())
        fail("Could not find all 15 category series in one year.\n"
             f"Series codes BEA returned: {found}")
    info(f"Using {chosen} (newest complete year)")

    # Convert everything to billions using BEA's unit multiplier.
    rows = []
    for _, c in cats.iterrows():
        value, mult = pick(t235, c["series_code"], chosen)
        rows.append({"year": chosen, "key": c["key"], "series_code": c["series_code"],
                     "value_billions": round(value * 10 ** mult / 1e9, 3)})
    bench = pd.DataFrame(rows)

    trow = total_rows[total_rows["year"] == chosen].dropna(subset=["value"]).iloc[0]
    total_b = float(trow["value"]) * 10 ** int(trow["unit_mult"]) / 1e9

    pc_value, pc_mult = pick(t71, PER_CAPITA_CODE, chosen)
    per_capita = pc_value * 10 ** pc_mult
    saving = pick(t21, SAVING_RATE_CODE, chosen)
    saving_rate = saving[0] if saving else None

    # Sanity checks so a unit mix-up is caught right away.
    leaf_sum = bench["value_billions"].sum()
    if not 0.9 < leaf_sum / total_b < 1.0:
        warn(f"The 15 categories add to {leaf_sum:,.0f}B vs total {total_b:,.0f}B "
             "(expected about 97%). Check units before trusting results.")
    if not 20_000 < per_capita < 200_000:
        warn(f"PCE per person came out as ${per_capita:,.0f}, which looks wrong. Check units.")
    if saving_rate is None:
        warn("Saving rate (A072RC) not found; saving-rate comparison will be skipped.")

    bench.to_csv(BENCHMARK_CSV, index=False)
    meta = {
        "year": chosen,
        "total_pce_billions": round(total_b, 3),
        "per_capita_pce": round(per_capita),
        "saving_rate_pct": saving_rate,
        "source": "BEA API: NIPA tables T20305, T70100, T20100 (annual)",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print()
    info(f"Saved {BENCHMARK_CSV.name} and {META_JSON.name}")
    print(f"     Year:                 {chosen}")
    print(f"     Total US PCE:         ${total_b:,.0f} billion")
    print(f"     PCE per person:       ${per_capita:,.0f}")
    if saving_rate is not None:
        print(f"     Personal saving rate: {saving_rate:.1f}%")
    print("\nCHECKPOINT: total PCE should be around $21,000 billion (about $21 trillion) "
          "and PCE per person around $60,000. Much bigger or smaller means a units problem.")


if __name__ == "__main__":
    main()
