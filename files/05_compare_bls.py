"""Step 5 (optional): compare your spending with the BLS Consumer Expenditure Survey.

Run:  python 05_compare_bls.py

Writes output/comparison_bls.csv and output/comparison_bls.png.

Why this is different from 03_compare.py's PCE comparison: PCE counts money
spent BY OR ON YOUR BEHALF, including what employers and government pay for
things like health care. CE only counts what a household pays out of pocket,
which is a closer match to what shows up in your bank statement.

This comparison reuses the categorization you already did in step 2 (the
pce_key on each transaction), then rolls those 15 PCE categories up into
BLS's 15 CE categories using the ce_key column in data/categories.csv. That
crosswalk is approximate - CE and PCE group things differently, and some
PCE categories are catch-alls that don't map cleanly to one CE bucket (see
the README). A few CE categories (alcohol, tobacco, reading, cash
contributions) have no PCE category feeding them, so they will always show
$0 for "You" here even if you do spend in those areas.

CE dollar figures are PER CONSUMER UNIT (BLS's version of a household), not
per person, so - unlike the PCE comparison - they are not multiplied by
HOUSEHOLD_SIZE.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # save to file, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd

from pce_common import (CATEGORIZED_CSV, COMPARISON_BLS_CSV, COMPARISON_BLS_PNG,
                        EXCLUDE, UNCATEGORIZED, fail, info, load_categories,
                        load_ce_benchmark, load_ce_categories, money, warn)

YOU_COLOR = "#2a78d6"   # blue
US_COLOR = "#2f9e6b"    # green (distinct from the PCE chart's orange)
INK = "#1f1f1e"
MUTED = "#6b6a63"
GRID = "#e4e3dc"


def main() -> None:
    if not CATEGORIZED_CSV.exists():
        fail("No categorized spending yet. Run:  python 02_categorize.py")

    cats = load_categories()
    if "ce_key" not in cats.columns:
        fail("data/categories.csv has no ce_key column. Re-download the project files.")
    ce_cats = load_ce_categories()
    ce_bench, meta = load_ce_benchmark()

    tx = pd.read_csv(CATEGORIZED_CSV, parse_dates=["date"])
    counted = tx[tx["pce_key"] != EXCLUDE]
    if counted.empty:
        fail("No spending rows to compare.")

    days = (counted["date"].max() - counted["date"].min()).days + 1
    months = days / 30.44
    if months < 3:
        warn(f"Your data covers only {months:.1f} months. Seasonal costs (holidays, "
             "insurance, travel) will be off. 12 months is best.")
    per_year = 12 / months

    pce_to_ce = dict(zip(cats["key"], cats["ce_key"]))
    mine_by_pce = (counted[counted["pce_key"] != UNCATEGORIZED]
                   .groupby("pce_key")["spend"].sum())
    mine = mine_by_pce.rename(index=pce_to_ce).groupby(level=0).sum()
    my_total = mine.sum()
    if my_total <= 0:
        fail("Nothing was categorized. Add rules to data/category_rules.csv.")

    table = ce_cats[["ce_key", "series_code", "label"]].copy()
    table["us_value"] = table["ce_key"].map(dict(zip(ce_bench["ce_key"], ce_bench["value"])))
    us_leaf_total = table["us_value"].sum()
    table["us_share_pct"] = table["us_value"] / us_leaf_total * 100
    table["my_spend_in_data"] = table["ce_key"].map(mine).fillna(0)
    table["my_per_year"] = table["my_spend_in_data"] * per_year
    table["my_share_pct"] = table["my_spend_in_data"] / my_total * 100
    table["share_diff_pts"] = table["my_share_pct"] - table["us_share_pct"]
    table["dollar_diff_per_year"] = table["my_per_year"] - table["us_value"]
    table = table.sort_values("us_share_pct", ascending=False)

    out = table[["label", "my_share_pct", "us_share_pct", "share_diff_pts",
                 "my_per_year", "us_value", "dollar_diff_per_year"]].round(2)
    out = out.rename(columns={"us_value": "us_per_year_per_consumer_unit"})
    out.to_csv(COMPARISON_BLS_CSV, index=False)

    print(f"\nYou vs. US Consumer Expenditure Survey ({meta['year']})")
    print(f"Your data: {counted['date'].min():%b %d, %Y} to {counted['date'].max():%b %d, %Y} "
          f"({months:.1f} months), scaled to a full year")
    print(f"US figures: average per consumer unit (BLS's version of a household), "
          f"NOT multiplied by HOUSEHOLD_SIZE.  Source: {meta['source']}\n")
    head = f"{'Category':<38}{'You %':>8}{'US %':>8}{'Diff':>8}{'You $/yr':>13}{'US $/yr':>13}"
    print(head)
    print("-" * len(head))
    for _, r in table.iterrows():
        print(f"{r['label']:<38}{r['my_share_pct']:>7.1f}%{r['us_share_pct']:>7.1f}%"
              f"{r['share_diff_pts']:>+7.1f} {money(r['my_per_year']):>12} {money(r['us_value']):>12}")
    print("-" * len(head))
    my_year_total = table["my_per_year"].sum()
    us_year_total = table["us_value"].sum()
    print(f"{'Total (categorized)':<38}{'':>8}{'':>8}{'':>8}{money(my_year_total):>13}"
          f"{money(us_year_total):>13}")

    zero_cats = table[table["my_spend_in_data"] == 0]["label"].tolist()
    if zero_cats:
        print(f"\nAlways $0 for you (no PCE category maps to these): {', '.join(zero_cats)}")

    top = table.sort_values("share_diff_pts", ascending=False)
    over = top[top["share_diff_pts"] >= 5]
    under = top[top["share_diff_pts"] <= -5].iloc[::-1]
    print("\nWhat stands out (5+ points different):")
    if over.empty and under.empty:
        print("  Your spending mix is within 5 points of the US in every category.")
    for _, r in over.iterrows():
        print(f"  Higher than US: {r['label']} ({r['share_diff_pts']:+.1f} pts)")
    for _, r in under.iterrows():
        print(f"  Lower than US:  {r['label']} ({r['share_diff_pts']:+.1f} pts)")

    print("\nKeep in mind:")
    print("  - This crosswalk from 15 PCE categories to 15 CE categories is approximate; "
          "some PCE catch-all categories (like 'other services') only map to one CE bucket.")
    print("  - CE health care should track your actual out-of-pocket costs better than "
          "the PCE comparison does.")
    print("  - Compare percentages first; dollar amounts depend on income and household size.")

    make_chart(table, meta, months)
    info(f"Saved {COMPARISON_BLS_CSV.name} and {COMPARISON_BLS_PNG.name} in the output folder")


def make_chart(table: pd.DataFrame, meta: dict, months: float) -> None:
    data = table.sort_values("us_share_pct")
    n = len(data)
    fig, ax = plt.subplots(figsize=(10, 0.48 * n + 1.8), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bar_h = 0.36
    gap = 0.02
    y = range(n)
    ax.barh([i + bar_h / 2 + gap for i in y], data["my_share_pct"], height=bar_h,
            color=YOU_COLOR, label="You", zorder=3)
    ax.barh([i - bar_h / 2 - gap for i in y], data["us_share_pct"], height=bar_h,
            color=US_COLOR, label=f"US average, CE ({meta['year']})", zorder=3)

    xmax = max(data["my_share_pct"].max(), data["us_share_pct"].max())
    for i, (_, r) in enumerate(data.iterrows()):
        if abs(r["share_diff_pts"]) >= 5:
            ax.text(max(r["my_share_pct"], r["us_share_pct"]) + xmax * 0.01, i,
                    f"{r['share_diff_pts']:+.0f} pts", va="center", fontsize=8.5,
                    color=INK, fontweight="bold")

    ax.set_yticks(list(y))
    ax.set_yticklabels(data["label"], fontsize=9, color=INK)
    ax.set_xlim(0, xmax * 1.15)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.tick_params(axis="x", colors=MUTED, labelsize=8.5)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)

    ax.set_title("Where the money goes: share of spending by category (CE survey)",
                 loc="left", fontsize=13, color=INK, fontweight="bold", pad=26)
    ax.text(0, 1.02, f"Your last {months:.0f} months vs. US Consumer Expenditure Survey, "
            f"{meta['year']} (out-of-pocket spending, per consumer unit)",
            transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    fig.text(0.01, 0.01, "Source: U.S. Bureau of Labor Statistics, Consumer Expenditure Survey. "
             "Category crosswalk from PCE is approximate.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(COMPARISON_BLS_PNG)
    plt.close(fig)


if __name__ == "__main__":
    main()
