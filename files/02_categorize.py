"""Step 2: read your bank/card CSV exports and sort each purchase into a PCE category.

Run:  python 02_categorize.py           (reads every .csv in data/raw)
      python 02_categorize.py --sample  (uses data/sample_transactions.csv to test)

Writes output/my_spending_categorized.csv and output/uncategorized.csv.
Improve results by adding lines to data/category_rules.csv and running again.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
from pathlib import Path

import pandas as pd

from pce_common import (BANK_MAP_CSV, CATEGORIZED_CSV, DATA, EXCLUDE, OUTPUT, RAW,
                        RULES_CSV, UNCATEGORIZED, UNCATEGORIZED_CSV, fail, info,
                        load_categories, setting, warn)

DATE_NAMES = ["transaction date", "trans. date", "trans date", "date", "posted date",
              "posting date", "post date"]
DESC_NAMES = ["description", "merchant", "payee", "name", "transaction description",
              "details", "memo"]
AMOUNT_NAMES = ["amount", "transaction amount", "amount (usd)"]
DEBIT_NAMES = ["debit", "withdrawal", "withdrawals", "debit amount"]
CREDIT_NAMES = ["credit", "deposit", "deposits", "credit amount"]
CATEGORY_NAMES = ["category", "transaction category"]


def read_bank_csv(path: Path) -> pd.DataFrame:
    """Read a bank export, skipping any summary lines above the real header."""
    text = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        fail(f"Could not read {path.name} (unknown text encoding).")
    lines = text.splitlines()
    date_word = (setting("CSV_DATE_COLUMN") or "date").lower()
    money_words = [w.lower() for w in (setting("CSV_AMOUNT_COLUMN"), setting("CSV_DEBIT_COLUMN")) if w]
    money_words = money_words or ["amount", "debit", "withdrawal"]
    header_idx = None
    for i, line in enumerate(lines[:30]):
        low = line.lower()
        if date_word in low and any(w in low for w in money_words):
            header_idx = i
            break
    if header_idx is None:
        fail(f"{path.name}: could not find a header row with 'date' and 'amount' "
             f"(or 'debit'). First line is: {lines[0] if lines else '(empty file)'}")
    body = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(body), dtype=str, skip_blank_lines=True,
                     quoting=csv.QUOTE_MINIMAL, on_bad_lines="warn")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_col(df: pd.DataFrame, override_setting: str, candidates: list[str]) -> str | None:
    override = setting(override_setting)
    lower = {c.lower(): c for c in df.columns}
    if override:
        if override.lower() in lower:
            return lower[override.lower()]
        fail(f"{override_setting}={override!r} in .env, but that column is not in the file. "
             f"Columns: {list(df.columns)}")
    for name in candidates:
        if name in lower:
            return lower[name]
    return None


def to_number(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip()
    negative = s.str.startswith("(") & s.str.endswith(")")
    s = s.str.replace(r"[\$,()\s]", "", regex=True)
    nums = pd.to_numeric(s, errors="coerce")
    nums[negative] = -nums[negative].abs()
    return nums


def normalize(path: Path) -> pd.DataFrame:
    df = read_bank_csv(path)
    date_col = find_col(df, "CSV_DATE_COLUMN", DATE_NAMES)
    desc_col = find_col(df, "CSV_DESCRIPTION_COLUMN", DESC_NAMES)
    amt_col = find_col(df, "CSV_AMOUNT_COLUMN", AMOUNT_NAMES)
    debit_col = find_col(df, "CSV_DEBIT_COLUMN", DEBIT_NAMES)
    credit_col = find_col(df, "CSV_CREDIT_COLUMN", CREDIT_NAMES)
    cat_col = find_col(df, "CSV_CATEGORY_COLUMN", CATEGORY_NAMES)

    if not date_col or not desc_col:
        fail(f"{path.name}: need a date and a description column. Columns: {list(df.columns)}\n"
             "Set CSV_DATE_COLUMN / CSV_DESCRIPTION_COLUMN in .env.")

    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "description": df[desc_col].fillna("").astype(str).str.strip(),
        "bank_category": df[cat_col].fillna("").astype(str).str.strip() if cat_col else "",
        "source_file": path.name,
    })

    if debit_col and not amt_col:
        # Separate Debit / Credit columns: debits are spending.
        debit = to_number(df[debit_col]).abs().fillna(0)
        credit = to_number(df[credit_col]).abs().fillna(0) if credit_col else 0
        out["spend"] = debit
        out["inflow"] = credit
        how = f"'{debit_col}' column = spending"
    elif amt_col:
        amount = to_number(df[amt_col])
        sign = setting("SPENDING_SIGN", "auto").lower()
        if sign not in ("auto", "negative", "positive"):
            fail("SPENDING_SIGN in .env must be auto, negative or positive.")
        if sign == "auto":
            sign = "negative" if (amount < 0).mean() >= 0.5 else "positive"
        if sign == "negative":
            out["spend"] = (-amount).clip(lower=0)
            out["inflow"] = amount.clip(lower=0)
        else:
            out["spend"] = amount.clip(lower=0)
            out["inflow"] = (-amount).clip(lower=0)
        how = f"'{amt_col}' column, {sign} numbers = spending"
    else:
        fail(f"{path.name}: no amount or debit column found. Columns: {list(df.columns)}\n"
             "Set CSV_AMOUNT_COLUMN or CSV_DEBIT_COLUMN in .env.")

    bad_dates = out["date"].isna().sum()
    if bad_dates:
        warn(f"{path.name}: {bad_dates} row(s) had no readable date and were skipped.")
    out = out.dropna(subset=["date"])
    out["spend"] = out["spend"].fillna(0)
    out["inflow"] = out["inflow"].fillna(0)
    info(f"{path.name}: {len(out)} rows, {out['date'].min():%Y-%m-%d} to "
         f"{out['date'].max():%Y-%m-%d}; reading {how}")
    return out


def compile_rules(valid_keys: set[str]) -> list[tuple[re.Pattern, str, str]]:
    if not RULES_CSV.exists():
        fail(f"Missing {RULES_CSV}. Run:\n"
             "  Copy-Item .\\data\\category_rules.example.csv .\\data\\category_rules.csv")
    rules = pd.read_csv(RULES_CSV, dtype=str).fillna("")
    compiled = []
    for _, r in rules.iterrows():
        kw = r["keyword"].strip().lower()
        key = r["pce_key"].strip()
        if not kw:
            continue
        if key not in valid_keys:
            fail(f"category_rules.csv: '{kw}' points to unknown category '{key}'. "
                 f"Use one of: {sorted(valid_keys)}")
        # Short keywords must match a whole word ("irs" should not match "first").
        pattern = r"(?<![a-z0-9])" + re.escape(kw)
        if len(kw) <= 4:
            pattern += r"(?![a-z0-9])"
        compiled.append((re.compile(pattern), key, kw))
    # Longer keywords first, so "uber eats" wins over "uber".
    compiled.sort(key=lambda t: len(t[2]), reverse=True)
    return compiled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", action="store_true",
                        help="use data/sample_transactions.csv instead of data/raw")
    args = parser.parse_args()

    OUTPUT.mkdir(exist_ok=True)
    if args.sample:
        files = [DATA / "sample_transactions.csv"]
        warn("Using SAMPLE data (made-up transactions), not your own.")
    else:
        files = sorted(RAW.glob("*.csv"))
        if not files:
            fail("No CSV files in data/raw. Export transactions from your bank as CSV "
                 "and save them there (or run with --sample to test).")

    frames = [normalize(f) for f in files]
    tx = pd.concat(frames, ignore_index=True)

    dupes = tx.duplicated(subset=["date", "description", "spend"], keep=False) & \
        tx.groupby(["date", "description", "spend"])["source_file"].transform("nunique").gt(1)
    if dupes.any():
        warn(f"{int(dupes.sum())} rows look identical across different files. "
             "If your exports overlap in dates, trim them so nothing is counted twice.")

    cats = load_categories()
    valid = set(cats["key"]) | {EXCLUDE}
    rules = compile_rules(valid)

    bank_map = {}
    if BANK_MAP_CSV.exists():
        bm = pd.read_csv(BANK_MAP_CSV, dtype=str).fillna("")
        bank_map = {r["bank_category"].strip().lower(): r["pce_key"].strip()
                    for _, r in bm.iterrows()}

    def categorize(row) -> tuple[str, str]:
        desc = row["description"].lower()
        for pattern, key, kw in rules:
            if pattern.search(desc):
                return key, f"rule: {kw}"
        bc = str(row["bank_category"]).strip().lower()
        if bc and bc in bank_map:
            return bank_map[bc], f"bank category: {row['bank_category']}"
        return UNCATEGORIZED, ""

    result = tx.apply(categorize, axis=1, result_type="expand")
    tx["pce_key"] = result[0]
    tx["matched_by"] = result[1]

    spending = tx[tx["spend"] > 0].copy()
    label_map = dict(zip(cats["key"], cats["label"]))
    spending["pce_label"] = spending["pce_key"].map(label_map).fillna(spending["pce_key"])
    spending = spending.sort_values("date")
    spending.to_csv(CATEGORIZED_CSV, index=False, date_format="%Y-%m-%d")

    unc = spending[spending["pce_key"] == UNCATEGORIZED]
    (unc.groupby("description", as_index=False)
        .agg(times=("spend", "size"), total=("spend", "sum"))
        .sort_values("total", ascending=False)
        .to_csv(UNCATEGORIZED_CSV, index=False))

    counted = spending[spending["pce_key"] != EXCLUDE]
    total = counted["spend"].sum()
    unc_total = unc["spend"].sum()
    print()
    info(f"Wrote {CATEGORIZED_CSV.relative_to(CATEGORIZED_CSV.parents[1])}")
    print(f"     Outflows counted as spending: ${total:,.2f}")
    print(f"     Excluded (payments, transfers, investing, taxes): "
          f"${spending.loc[spending['pce_key'] == EXCLUDE, 'spend'].sum():,.2f}")
    share = (unc_total / total * 100) if total else 0
    print(f"     Uncategorized: ${unc_total:,.2f} ({share:.1f}% of spending)")
    print()
    print("Spending by category:")
    summary = (counted.groupby("pce_label")["spend"].sum().sort_values(ascending=False))
    for label, value in summary.items():
        print(f"     {label:<40} ${value:>12,.2f}")
    print()
    if share > 10:
        print("CHECKPOINT: more than 10% is uncategorized. Open output/uncategorized.csv, "
              "add keywords to data/category_rules.csv, and run this step again.")
    else:
        print("CHECKPOINT: under 10% uncategorized - good enough to compare. "
              "Skim output/my_spending_categorized.csv for anything in the wrong bucket.")


if __name__ == "__main__":
    main()
