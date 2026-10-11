"""Step 0: check that Python, packages, settings and folders are ready.

Run:  python 00_check_setup.py
"""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
problems = 0


def ok(msg):
    print(f"  [OK]   {msg}")


def bad(msg):
    global problems
    problems += 1
    print(f"  [FIX]  {msg}")


def note(msg):
    print(f"  [NOTE] {msg}")


print("\n1) Python version")
if sys.version_info >= (3, 9):
    ok(f"Python {sys.version.split()[0]}")
else:
    bad(f"Python {sys.version.split()[0]} is too old. Install Python 3.9 or newer.")

print("\n2) Packages")
for module, pip_name in [("pandas", "pandas"), ("matplotlib", "matplotlib"),
                         ("beaapi", "beaapi"), ("dotenv", "python-dotenv")]:
    try:
        mod = importlib.import_module(module)
        ok(f"{pip_name} {getattr(mod, '__version__', '')}".strip())
    except ImportError:
        bad(f"{pip_name} is missing. Run:  python -m pip install -r requirements.txt")

print("\n3) Virtual environment")
if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
    ok(f"Running inside a virtual environment ({sys.prefix})")
else:
    note("Not inside a virtual environment. It still works, but activating .venv is recommended.")

print("\n4) Settings file (.env)")
env_path = ROOT / ".env"
if not env_path.exists():
    bad("No .env file. Copy .env.example to .env and fill it in.")
else:
    ok(".env found")
    try:
        from dotenv import dotenv_values

        values = dotenv_values(env_path)
        key = (values.get("BEA_API_KEY") or "").strip()
        if not key or key.lower().startswith("paste"):
            note("BEA_API_KEY is empty. You can still test with:  python 01_fetch_pce.py --offline")
        elif len(key) != 36:
            bad(f"BEA_API_KEY is {len(key)} characters; BEA keys are 36. Check for extra spaces or quotes.")
        else:
            ok(f"BEA_API_KEY looks right (ends in ...{key[-4:]})")
        size = (values.get("HOUSEHOLD_SIZE") or "1").strip()
        ok(f"HOUSEHOLD_SIZE = {size}")
        income = (values.get("ANNUAL_TAKE_HOME") or "").strip()
        if income:
            ok("ANNUAL_TAKE_HOME is set (saving-rate comparison will run)")
        else:
            note("ANNUAL_TAKE_HOME is blank (saving-rate comparison will be skipped)")
        bls_key = (values.get("BLS_API_KEY") or "").strip()
        if bls_key:
            ok(f"BLS_API_KEY is set (ends in ...{bls_key[-4:]}) - optional step 04/05 will run")
        else:
            note("BLS_API_KEY is blank. Optional: get one at "
                 "https://www.bls.gov/developers/api_signature_v2.htm for the CE comparison, "
                 "or run:  python 04_fetch_bls.py --offline")
        fred_key = (values.get("FRED_API_KEY") or "").strip()
        if fred_key:
            ok(f"FRED_API_KEY is set (ends in ...{fred_key[-4:]}) - optional step 07/08 will run")
        else:
            note("FRED_API_KEY is blank. Optional: get one at "
                 "https://fredaccount.stlouisfed.org/apikeys for the national trend chart, "
                 "or run:  python 07_fetch_fred.py --offline")
    except ImportError:
        note("Install python-dotenv to check the .env contents.")

print("\n5) Category rules file")
rules_path = ROOT / "data" / "category_rules.csv"
if rules_path.exists():
    ok("data/category_rules.csv found")
else:
    bad("No data/category_rules.csv. Run:  "
        "Copy-Item .\\data\\category_rules.example.csv .\\data\\category_rules.csv")

print("\n6) Your bank CSV files (data/raw)")
raw = ROOT / "data" / "raw"
if not raw.exists():
    bad("data/raw folder is missing. Create it and put your bank CSV exports inside.")
else:
    files = sorted(raw.glob("*.csv"))
    if files:
        ok(f"{len(files)} CSV file(s): " + ", ".join(f.name for f in files))
    else:
        note("No CSV files yet. Put bank exports in data/raw, "
             "or test with:  python 02_categorize.py --sample")

print("\n7) .gitignore protects your data")
gi = ROOT / ".gitignore"
gi_text = gi.read_text(encoding="utf-8") if gi.exists() else ""
if gi.exists() and "data/raw" in gi_text and ".env" in gi_text and "category_rules.csv" in gi_text:
    ok(".gitignore excludes .env, data/raw, and your personal category_rules.csv")
else:
    bad(".gitignore is missing or incomplete. Re-download it before using git.")

print()
if problems:
    print(f"RESULT: {problems} thing(s) to fix above.")
    sys.exit(1)
print("RESULT: Setup looks good.")
