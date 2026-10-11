"""Step 3: compare your spending with US Personal Consumption Expenditures.

Run:  python 03_compare.py

Writes output/comparison.csv (the numbers) and output/comparison.png (the chart).

Two comparisons:
  1. Share of spending - what % of your budget goes to each category vs the US.
     This is the fairest comparison, because it doesn't depend on income.
  2. Dollars per year - your yearly pace vs the US average per person
     (times HOUSEHOLD_SIZE from .env).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # save to file, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd

from pce_common import (CATEGORIZED_CSV, COMPARISON_CSV, COMPARISON_PNG, EXCLUDE,
                        UNCATEGORIZED, fail, info, load_benchmark, load_categories,
                        money, setting_float, warn)

YOU_COLOR = "#2a78d6"   # blue
US_COLOR = "#eb6834"    # orange
INK = "#1f1f1e"
MUTED = "#6b6a63"
GRID = "#e4e3dc"


def main() -> None:
    if not CATEGORIZED_CSV.exists():
        fail("No categorized spending yet. Run:  python 02_categorize.py")

    cats = load_categories()
    bench, meta = load_benchmark()
    household = setting_float("HOUSEHOLD_SIZE", 1.0) or 1.0
    take_home = setting_float("ANNUAL_TAKE_HOME", None)

    tx = pd.read_csv(CATEGORIZED_CSV, parse_dates=["date"])
    counted = tx[tx["pce_key"] != EXCLUDE]
    if counted.empty:
        fail("No spending rows to compare.")

    # How much time the data covers, so we can scale to a full year.
    days = (counted["date"].max() - counted["date"].min()).days + 1
    months = days / 30.44
    if months < 3:
        warn(f"Your data covers only {months:.1f} months. Seasonal costs (holidays, "
             "insurance, travel) will be off. 12 months is best.")
    per_year = 12 / months

    unc_total = counted.loc[counted["pce_key"] == UNCATEGORIZED, "spend"].sum()
    mine = (counted[counted["pce_key"] != UNCATEGORIZED]
            .groupby("pce_key")["spend"].sum())
    my_total = mine.sum()
    if my_total <= 0:
        fail("Nothing was categorized. Add rules to data/category_rules.csv.")

    # US: shares of household spending across the 15 categories, and $ per person.
    bench = bench.merge(cats, on=["key", "series_code"], how="left")
    us_leaf_total = bench["value_billions"].sum()
    per_person_factor = meta["per_capita_pce"] / meta["total_pce_billions"]  # $ per person per $1B

    table = bench[["key", "label", "group", "value_billions"]].copy()
    table["us_share_pct"] = table["value_billions"] / us_leaf_total * 100
    table["us_per_year"] = table["value_billions"] * per_person_factor * household
    table["my_spend_in_data"] = table["key"].map(mine).fillna(0)
    table["my_per_year"] = table["my_spend_in_data"] * per_year
    table["my_share_pct"] = table["my_spend_in_data"] / my_total * 100
    table["share_diff_pts"] = table["my_share_pct"] - table["us_share_pct"]
    table["dollar_diff_per_year"] = table["my_per_year"] - table["us_per_year"]
    table = table.sort_values("us_share_pct", ascending=False)

    out = table[["group", "label", "my_share_pct", "us_share_pct", "share_diff_pts",
                 "my_per_year", "us_per_year", "dollar_diff_per_year"]].round(2)
    out.to_csv(COMPARISON_CSV, index=False)

    # ---------- Terminal report ----------
    who = "per person" if household == 1 else f"for {household:g} people"
    print(f"\nYou vs. US PCE ({meta['year']})")
    print(f"Your data: {counted['date'].min():%b %d, %Y} to {counted['date'].max():%b %d, %Y} "
          f"({months:.1f} months), scaled to a full year")
    print(f"US figures: average {who}.  Source: {meta['source']}\n")
    head = f"{'Category':<38}{'You %':>8}{'US %':>8}{'Diff':>8}{'You $/yr':>13}{'US $/yr':>13}"
    print(head)
    print("-" * len(head))
    for _, r in table.iterrows():
        print(f"{r['label']:<38}{r['my_share_pct']:>7.1f}%{r['us_share_pct']:>7.1f}%"
              f"{r['share_diff_pts']:>+7.1f} {money(r['my_per_year']):>12} {money(r['us_per_year']):>12}")
    print("-" * len(head))
    my_year_total = table["my_per_year"].sum()
    us_year_total = table["us_per_year"].sum()
    print(f"{'Total (categorized)':<38}{'':>8}{'':>8}{'':>8}{money(my_year_total):>13}"
          f"{money(us_year_total):>13}")
    if unc_total > 0:
        unc_share = unc_total / (my_total + unc_total) * 100
        print(f"\nNot included above: {money(unc_total)} uncategorized ({unc_share:.1f}% of "
              "your spending).")

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

    # Saving rate: (take-home - spending) / take-home, vs BEA's personal saving rate.
    if take_home and meta.get("saving_rate_pct") is not None:
        total_spend_year = (my_total + unc_total) * per_year
        my_rate = (take_home - total_spend_year) / take_home * 100
        print(f"\nSaving rate: you {my_rate:.1f}%  vs  US {meta['saving_rate_pct']:.1f}%")
        print("  (Yours = take-home pay minus all counted spending, divided by take-home pay.)")
    elif not take_home:
        print("\nSaving rate skipped: set ANNUAL_TAKE_HOME in .env to include it.")

    print("\nKeep in mind:")
    print("  - US health care includes what employers and government pay for people, "
          "so it looks much higher than out-of-pocket costs.")
    print("  - US housing includes an estimated rent for people who own their home.")
    print("  - Compare percentages first; dollar amounts depend on income and where you live.")

    # ---------- Chart ----------
    make_chart(table, meta, months)
    info(f"Saved {COMPARISON_CSV.name} and {COMPARISON_PNG.name} in the output folder")


def make_chart(table: pd.DataFrame, meta: dict, months: float) -> None:
    data = table.sort_values("us_share_pct")  # biggest US category at the top
    n = len(data)
    fig, ax = plt.subplots(figsize=(10, 0.48 * n + 1.8), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bar_h = 0.36
    gap = 0.02  # small white gap between the pair of bars
    y = range(n)
    ax.barh([i + bar_h / 2 + gap for i in y], data["my_share_pct"], height=bar_h,
            color=YOU_COLOR, label="You", zorder=3)
    ax.barh([i - bar_h / 2 - gap for i in y], data["us_share_pct"], height=bar_h,
            color=US_COLOR, label=f"US average ({meta['year']})", zorder=3)

    # Label only the rows where you differ a lot, to keep it readable.
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

    ax.set_title("Where the money goes: share of spending by category",
                 loc="left", fontsize=13, color=INK, fontweight="bold", pad=26)
    ax.text(0, 1.02, f"Your last {months:.0f} months vs. US Personal Consumption "
            f"Expenditures, {meta['year']}", transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    fig.text(0.01, 0.01, "Source: U.S. Bureau of Economic Analysis, NIPA Table 2.3.5. "
             "US health care includes employer and government payments.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(COMPARISON_PNG)
    plt.close(fig)


if __name__ == "__main__":
    main()
