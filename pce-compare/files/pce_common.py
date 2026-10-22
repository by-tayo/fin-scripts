"""Shared paths, settings and helpers for the PCE comparison project."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
OFFLINE = DATA / "offline"
OUTPUT = ROOT / "output"

CATEGORIES_CSV = DATA / "categories.csv"
RULES_CSV = DATA / "category_rules.csv"
BANK_MAP_CSV = DATA / "bank_category_map.csv"
BENCHMARK_CSV = DATA / "pce_benchmark.csv"
META_JSON = DATA / "us_meta.json"
CATEGORIZED_CSV = OUTPUT / "my_spending_categorized.csv"
UNCATEGORIZED_CSV = OUTPUT / "uncategorized.csv"
COMPARISON_CSV = OUTPUT / "comparison.csv"
COMPARISON_PNG = OUTPUT / "comparison.png"

CE_CATEGORIES_CSV = DATA / "ce_categories.csv"
CE_BENCHMARK_CSV = DATA / "ce_benchmark.csv"
CE_META_JSON = DATA / "us_ce_meta.json"
COMPARISON_BLS_CSV = OUTPUT / "comparison_bls.csv"
COMPARISON_BLS_PNG = OUTPUT / "comparison_bls.png"

FRED_TREND_CSV = DATA / "fred_trend.csv"
FRED_META_JSON = DATA / "us_fred_meta.json"
TREND_NATIONAL_CSV = OUTPUT / "trend_national.csv"
TREND_NATIONAL_PNG = OUTPUT / "trend_national.png"

EXCLUDE = "EXCLUDE"
UNCATEGORIZED = "UNCATEGORIZED"

# Load settings from .env if python-dotenv is installed.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # 00_check_setup.py reports this
    pass


def setting(name: str, default: str = "") -> str:
    """Read a setting from .env / the environment, trimmed."""
    return os.getenv(name, default).strip()


def setting_float(name: str, default: float | None = None) -> float | None:
    raw = setting(name)
    if raw == "":
        return default
    try:
        return float(raw.replace(",", "").replace("$", ""))
    except ValueError:
        fail(f"{name} in .env must be a number, got: {raw!r}")
    return default


def fail(message: str) -> None:
    """Print a clear error and stop."""
    print(f"\n[ERROR] {message}\n")
    sys.exit(1)


def info(message: str) -> None:
    print(f"[OK] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def load_categories() -> pd.DataFrame:
    if not CATEGORIES_CSV.exists():
        fail(f"Missing {CATEGORIES_CSV}. Re-download the project files.")
    return pd.read_csv(CATEGORIES_CSV, dtype=str)


def load_benchmark() -> tuple[pd.DataFrame, dict]:
    """Load the US numbers written by 01_fetch_pce.py."""
    if not BENCHMARK_CSV.exists() or not META_JSON.exists():
        fail("No US benchmark yet. Run:  python 01_fetch_pce.py   "
             "(or  python 01_fetch_pce.py --offline  to use the saved snapshot)")
    bench = pd.read_csv(BENCHMARK_CSV, dtype={"key": str, "series_code": str})
    meta = json.loads(META_JSON.read_text(encoding="utf-8"))
    return bench, meta


def load_ce_categories() -> pd.DataFrame:
    if not CE_CATEGORIES_CSV.exists():
        fail(f"Missing {CE_CATEGORIES_CSV}. Re-download the project files.")
    return pd.read_csv(CE_CATEGORIES_CSV, dtype=str)


def load_ce_benchmark() -> tuple[pd.DataFrame, dict]:
    """Load the US Consumer Expenditure Survey numbers written by 04_fetch_bls.py."""
    if not CE_BENCHMARK_CSV.exists() or not CE_META_JSON.exists():
        fail("No BLS CE benchmark yet. Run:  python 04_fetch_bls.py   "
             "(or  python 04_fetch_bls.py --offline  to use the saved snapshot)")
    bench = pd.read_csv(CE_BENCHMARK_CSV, dtype={"ce_key": str, "series_code": str})
    meta = json.loads(CE_META_JSON.read_text(encoding="utf-8"))
    return bench, meta


def load_fred_trend() -> tuple[pd.DataFrame, dict]:
    """Load the national monthly PCE/inflation trend written by 07_fetch_fred.py."""
    if not FRED_TREND_CSV.exists() or not FRED_META_JSON.exists():
        fail("No FRED trend data yet. Run:  python 07_fetch_fred.py   "
             "(or  python 07_fetch_fred.py --offline  to use the saved snapshot)")
    trend = pd.read_csv(FRED_TREND_CSV, parse_dates=["date"])
    meta = json.loads(FRED_META_JSON.read_text(encoding="utf-8"))
    return trend, meta


def money(x: float) -> str:
    return f"${x:,.0f}"
