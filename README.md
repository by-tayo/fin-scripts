# PCE Compare: my spending vs. the US

This project compares your own spending with **Personal Consumption Expenditures (PCE)**, the government's measure of what US households spend. The Bureau of Economic Analysis (BEA) publishes it, and it's the "C" (consumption) in GDP.

It answers three questions:

1. **Mix:** what % of my spending goes to housing, food, transportation and so on, compared with the US?
2. **Dollars:** how does my yearly spending in each category compare with the average American's?
3. **Saving:** how does my saving rate compare with the US personal saving rate?

There's also an optional fourth comparison against the **BLS Consumer Expenditure Survey (CE)**, which tracks what households pay out of pocket rather than PCE's broader measure (which also counts what employers and government pay on people's behalf). CE is a closer match to your own budget, especially for health care. See "Optional: compare against the BLS Consumer Expenditure Survey" below.

---

## Tools

| Tool | What it's for | Cost |
|---|---|---|
| Python 3.9+ | Runs the scripts | Free |
| VS Code (optional) | Editing files and running the terminal | Free |
| pandas | Reading and summarizing your bank CSVs | Free |
| matplotlib | Drawing the comparison chart | Free |
| beaapi | BEA's official Python library for their data | Free |
| python-dotenv | Loads your API key from a `.env` file so it stays out of the code | Free |
| BEA API key | Access to PCE data | Free (sign up with name and email) |
| BLS API key (optional) | Access to CE data, for the optional Step 4/5 comparison | Free (sign up with name and email) |
| Bank/card CSV exports | Your spending | Free, from your bank's website |

## What's in the folder

```
pce-compare/
├── 00_check_setup.py        Step 0: checks your setup
├── 01_fetch_pce.py          Step 1: downloads US PCE data from BEA
├── 02_categorize.py         Step 2: sorts your transactions into PCE categories
├── 03_compare.py            Step 3: builds the PCE comparison report and chart
├── 04_fetch_bls.py          Step 4 (optional): downloads US CE data from BLS
├── 05_compare_bls.py        Step 5 (optional): builds the CE comparison report and chart
├── pce_common.py            Shared helper code
├── requirements.txt         Python packages
├── .env.example             Settings template (copy it to .env)
├── .gitignore               Keeps your key and bank data out of git
├── data/
│   ├── categories.csv       The 15 PCE categories, their BEA series codes, and their CE crosswalk
│   ├── category_rules.example.csv  Generic starter keyword → category rules (copy to category_rules.csv)
│   ├── category_rules.csv   Your real rules, including personal ones (gitignored - not pushed to GitHub)
│   ├── bank_category_map.csv  Your bank's own categories → PCE categories
│   ├── ce_categories.csv    The 15 BLS CE categories and their series codes
│   ├── sample_transactions.csv  Made-up data for testing
│   ├── offline/             Saved US numbers for testing without a key (PCE and CE)
│   └── raw/                 PUT YOUR BANK CSV FILES HERE
└── output/                  Results show up here
```

---

## Setup (Windows, PowerShell)

Open **PowerShell** in the `pce-compare` folder. In File Explorer, open the folder, click the address bar, type `powershell` and press Enter.

### Step 1: Check Python

```powershell
if (Get-Command python -ErrorAction SilentlyContinue) { python --version } else { Write-Host "Python not found. Install it from https://www.python.org/downloads/ and CHECK 'Add python.exe to PATH'." }
```

✅ **Checkpoint:** you see `Python 3.9` or higher. If Windows opens the Microsoft Store instead, install Python from python.org, then close and reopen PowerShell.

### Step 2: Confirm you're in the right folder

```powershell
if (Test-Path .\01_fetch_pce.py) { Write-Host "Correct folder: $(Get-Location)" } else { Write-Host "Not in pce-compare. Found here:"; Get-ChildItem -Name }
```

✅ **Checkpoint:** you see "Correct folder."

### Step 3: Create and turn on a virtual environment

A virtual environment keeps this project's packages separate from everything else on your computer.

```powershell
if (-not (Test-Path .\.venv)) { python -m venv .venv; Write-Host "Created .venv" } else { Write-Host ".venv already exists" }
.\.venv\Scripts\Activate.ps1
```

If you get a "running scripts is disabled" error, run this once, then run the activate line again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

✅ **Checkpoint:** your prompt starts with `(.venv)`.

### Step 4: Install packages

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

✅ **Checkpoint:** the last line says `Successfully installed ...` (or "Requirement already satisfied").

### Step 5: Get your free BEA API key

1. Go to **https://apps.bea.gov/api/signup/**
2. Enter your name and email.
3. BEA emails you a 36-character key. **Click the activation link in that email.** The key won't work until you do.

✅ **Checkpoint:** you have the key and clicked the activation link.

### Step 6: Create your settings file

```powershell
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env; Write-Host "Created .env" } else { Write-Host ".env already exists - not overwriting" }
notepad .env
```

In Notepad, fill in:

- `BEA_API_KEY=`: paste your key with no quotes and no spaces.
- `HOUSEHOLD_SIZE=`: how many people your spending covers.
- `ANNUAL_TAKE_HOME=`: optional. Enter your yearly pay after taxes, numbers only.
- `BLS_API_KEY=`: optional, only needed for Step 4/5 (the CE comparison). Get one free at https://www.bls.gov/developers/api_signature_v2.htm - it doesn't need email activation like the BEA key, but **renew it once a year**.

Save and close Notepad.

### Step 6b: Create your category rules file

```powershell
if (-not (Test-Path .\data\category_rules.csv)) { Copy-Item .\data\category_rules.example.csv .\data\category_rules.csv; Write-Host "Created data\category_rules.csv" } else { Write-Host "data\category_rules.csv already exists - not overwriting" }
```

`category_rules.csv` is gitignored, since over time you'll add personal keywords to it (a roommate's name on Zelle, your landlord, your specific bank's transaction patterns). `category_rules.example.csv` stays generic and safe to share; your real one stays local.

### Step 7: Run the setup check

```powershell
python 00_check_setup.py
```

✅ **Checkpoint:** the last line says `RESULT: Setup looks good.` If you see `[FIX]` lines, do what they say and run the check again.

---

## Test run with sample data

Do this once before using your real data, so you know everything works.

```powershell
python 01_fetch_pce.py --offline
python 02_categorize.py --sample
python 03_compare.py
```

✅ **Checkpoint:** you see a table comparing "You %" and "US %", and `output\comparison.png` exists. Open the chart:

```powershell
if (Test-Path .\output\comparison.png) { Start-Process .\output\comparison.png } else { Write-Host "Chart not found - scroll up for an [ERROR] line" }
```

---

## Real run

### Step A: Download current US data

```powershell
python 01_fetch_pce.py
```

✅ **Checkpoint:** you see the year, total PCE (about $21,000 billion) and PCE per person (about $60,000). If you get an error about the key, check `.env` and make sure you clicked BEA's activation link.

### Step B: Export your transactions

On your bank's and card's websites, look for **Download / Export → CSV** for each account you spend from.

- Pick **12 months** if you can. Fewer months misses things like holiday shopping and yearly bills.
- Include checking **and** credit cards, but make sure the date ranges don't overlap within the same account.
- Save the files into `data\raw\`.

```powershell
$files = Get-ChildItem .\data\raw\*.csv -ErrorAction SilentlyContinue
if ($files) { $files | Select-Object Name, Length } else { Write-Host "No CSV files in data\raw yet" }
```

✅ **Checkpoint:** your CSV files are listed.

> **Privacy:** your bank files stay on your computer. `.gitignore` keeps `data/raw/`, `output/` and `.env` out of git, so they won't be pushed to GitHub.

### Step C: Categorize

```powershell
python 02_categorize.py
```

For each file, the script tells you how it read the amounts, e.g. `'Amount' column, negative numbers = spending`.

✅ **Checkpoint 1:** that sentence is right for your bank. If it has spending backwards, set `SPENDING_SIGN=negative` or `SPENDING_SIGN=positive` in `.env` and run it again.

✅ **Checkpoint 2:** uncategorized is under 10%. If it isn't:

1. Open `output\uncategorized.csv`. It lists the biggest unmatched merchants first.
2. Open `data\category_rules.csv` and add a line for each, like `sunset apartments,housing_utilities,`
3. Run `python 02_categorize.py` again.

Category keys you can use:

| key | PCE category |
|---|---|
| `housing_utilities` | Rent, mortgage, electric, water |
| `groceries` | Food and drinks for home |
| `food_services` | Restaurants, takeout, hotels |
| `gasoline` | Gas stations |
| `transport_services` | Rideshare, flights, parking, tolls, car repair |
| `motor_vehicles` | Buying a car, car parts |
| `health_care` | Doctor, dentist, hospital, health insurance |
| `financial_insurance` | Car/renters insurance, bank fees, interest |
| `rec_services` | Streaming, gym, movies, concerts |
| `rec_goods` | Electronics, video games, sports gear |
| `furnishings` | Furniture, appliances, home improvement |
| `clothing` | Clothes and shoes |
| `other_nondurables` | Household supplies, medicine, personal care products |
| `other_durables` | Jewelry, books, luggage |
| `other_services` | Phone, internet, education, haircuts, childcare |
| `EXCLUDE` | **Not spending:** card payments, transfers, saving, investing, taxes |

Rule tips:

- Keywords aren't case-sensitive, and longer keywords are checked first.
- Keywords of 4 letters or fewer must match a whole word, so `irs` won't match "FIRST WATCH".
- Zelle, Venmo and ATM withdrawals are left uncategorized on purpose. Add rules for the ones you can identify, like your rent.

### Step D: Compare

```powershell
python 03_compare.py
Start-Process .\output\comparison.png
```

The output folder then contains:

- `comparison.csv`: the full table. It opens in Excel.
- `comparison.png`: the chart.
- `my_spending_categorized.csv`: every transaction with its category, for double-checking.

---

## Optional: compare against the BLS Consumer Expenditure Survey

Do this after Step D. It reuses the categorization from Step C, so no new categorizing needed.

```powershell
python 04_fetch_bls.py
python 05_compare_bls.py
Start-Process .\output\comparison_bls.png
```

(`python 04_fetch_bls.py --offline` works too, using a saved 2024 snapshot, if you don't have a BLS key yet.)

This produces `output\comparison_bls.csv` and `output\comparison_bls.png`, in the same format as the PCE comparison.

**Why bother with a second comparison?** PCE counts money spent *by or on your behalf* - including what employers and government pay for things like health care - which is why the PCE comparison makes your health care spending look tiny. CE only counts what a household actually pays out of pocket, which is a much closer match to what shows up in your bank statement.

**The category crosswalk is approximate.** CE and PCE group spending differently, so `data\categories.csv` has a `ce_key` column mapping each of the 15 PCE categories to the closest of BLS's 15 CE categories. Some PCE categories are catch-alls (like `other_nondurables` or `other_services`) that don't map cleanly to a single CE bucket - the script's output tells you which CE categories these fall into. A few CE categories (alcohol, tobacco, reading, cash contributions) have no PCE category feeding them at all, so they'll always show $0 for "You" even if you do spend there - the report lists these explicitly so you know they're not real zeros.

**CE dollars are per "consumer unit"** (BLS's version of a household), not per person - unlike the PCE comparison, they are **not** multiplied by `HOUSEHOLD_SIZE`.

---

## How to read the results

- **Start with the percentages.** The share of spending doesn't depend on how much you earn, so it's the fairest comparison.
- **Health care will look low for you.** US PCE counts what employers and government programs (like Medicare) pay for people, not just what they pay out of pocket.
- **Housing is measured differently.** PCE includes an estimated rent for homeowners. If you rent, your rent is a direct comparison.
- **The US numbers are averages** across every age, income and city. A student in San Antonio won't look like the national average, and that's expected.
- **Saving rate:** yours is (take-home pay − spending) ÷ take-home pay. BEA's rate is saving as a share of disposable personal income, which is close to the same idea.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` opens the Microsoft Store | Install from python.org with "Add to PATH" checked, then reopen PowerShell |
| `Activate.ps1 cannot be loaded` | Run the `Set-ExecutionPolicy` line from Step 3 |
| `No module named ...` | The virtual environment isn't on. Run `.\.venv\Scripts\Activate.ps1`, then Step 4 |
| BEA key error | Check for spaces or quotes in `.env`, and click the activation link in BEA's email |
| `could not find a header row` | Your bank's CSV has an unusual layout. Set the `CSV_..._COLUMN` names in `.env` to match its header |
| Spending looks doubled | Two exports overlap in dates. Trim one of them |

## Where the data comes from

- **BEA NIPA Table 2.3.5**, Personal Consumption Expenditures by Major Type of Product (annual): the 15 categories and total PCE
- **BEA NIPA Table 7.1**, series A794RC: PCE per person
- **BEA NIPA Table 2.1**, series A072RC: personal saving rate
- The `--offline` snapshot uses 2025 values from these series as posted on FRED (April 9, 2026 update). BEA revises its numbers, so use the live API for real results.
- **BLS Consumer Expenditure Survey**, series `CXU...LB0101M` ("All Consumer Units", mean annual expenditure per consumer unit): the 15 CE categories used in the optional Step 4/5 comparison. The `--offline` snapshot uses 2024 values pulled directly from the BLS API. BLS revises its numbers too, so use the live API for real results.

## Ideas for later

- Add FRED data (free key at fredaccount.stlouisfed.org) to track how PCE and inflation change month to month.
- Write it up for LAY/ERD: "How does my budget compare to America's?"
