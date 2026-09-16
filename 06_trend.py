"""Step 6 (optional): see how your spending changed month to month.

Run:  python 06_trend.py

Writes output/trend.csv and output/trend.png.

Uses the same categorized transactions as 03_compare.py (output from step 2),
grouped by month instead of annualized into one snapshot. Useful for spotting
seasonal spikes (holidays, annual insurance, travel) that the single-number
comparison in step 3 smooths away.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # save to file, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd

from pce_common import CATEGORIZED_CSV, EXCLUDE, OUTPUT, fail, info

TREND_CSV = OUTPUT / "trend.csv"
TREND_PNG = OUTPUT / "trend.png"

# Fixed categorical order from the project's design palette - assigned by slot,
# never cycled or reassigned when the category list changes.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
OTHER_COLOR = "#c3c2b7"
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
TOP_N = 6


def main() -> None:
    if not CATEGORIZED_CSV.exists():
        fail("No categorized spending yet. Run:  python 02_categorize.py")

    tx = pd.read_csv(CATEGORIZED_CSV, parse_dates=["date"])
    counted = tx[tx["pce_key"] != EXCLUDE].copy()
    if counted.empty:
        fail("No spending rows to chart.")

    counted["month"] = counted["date"].dt.to_period("M").dt.to_timestamp()
    n_months = counted["month"].nunique()
    if n_months < 2:
        fail("Only one month of data - nothing to trend yet. Add more statements to data/raw.")

    by_month_cat = (counted.groupby(["month", "pce_label"])["spend"]
                     .sum().unstack(fill_value=0).sort_index())

    totals_by_cat = by_month_cat.sum().sort_values(ascending=False)
    top = list(totals_by_cat.index[:TOP_N])
    rest = [c for c in by_month_cat.columns if c not in top]
    chart_df = by_month_cat[top].copy()
    if rest:
        chart_df["Other"] = by_month_cat[rest].sum(axis=1)

    chart_df.to_csv(TREND_CSV)

    print(f"\nMonthly spending, {chart_df.index.min():%b %Y} to {chart_df.index.max():%b %Y}\n")
    col_w = 13
    header = f"{'Month':<10}" + "".join(f"{c[:col_w-1]:>{col_w}}" for c in chart_df.columns) + f"{'Total':>{col_w}}"
    print(header)
    print("-" * len(header))
    for idx, row in chart_df.iterrows():
        month_label = f"{idx:%b %Y}"
        line = f"{month_label:<10}" + "".join(f"${v:>{col_w-2},.0f}" for v in row) + f"${row.sum():>{col_w-2},.0f}"
        print(line)
    avg_total = chart_df.sum(axis=1).mean()
    peak_month = chart_df.sum(axis=1).idxmax()
    peak_value = chart_df.sum(axis=1).max()
    print(f"\nAverage month: ${avg_total:,.0f}   Highest month: {peak_month:%b %Y} (${peak_value:,.0f})")

    make_chart(chart_df)
    info(f"Saved {TREND_CSV.name} and {TREND_PNG.name} in the output folder")


def make_chart(chart_df: pd.DataFrame) -> None:
    n_series = len(chart_df.columns)
    colors = PALETTE[:n_series]
    if "Other" in chart_df.columns:
        colors = PALETTE[:n_series - 1] + [OTHER_COLOR]

    fig, ax = plt.subplots(figsize=(max(8, 0.9 * len(chart_df) + 3), 6), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x_labels = [d.strftime("%b %Y") for d in chart_df.index]
    x = range(len(chart_df))
    bottom = pd.Series(0.0, index=chart_df.index)
    for col, color in zip(chart_df.columns, colors):
        ax.bar(x, chart_df[col], bottom=bottom.values, width=0.62, color=color,
               label=col, zorder=3, edgecolor="white", linewidth=0.6)
        bottom += chart_df[col]

    totals = chart_df.sum(axis=1)
    for i, total in enumerate(totals):
        ax.text(i, total + totals.max() * 0.015, f"${total:,.0f}", ha="center",
                va="bottom", fontsize=8, color=INK, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(x_labels, fontsize=9, color=INK)
    ax.set_ylim(0, totals.max() * 1.15)
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("${x:,.0f}"))
    ax.tick_params(axis="y", colors=MUTED, labelsize=8.5)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)

    ax.set_title("Monthly spending by category", loc="left", fontsize=13,
                 color=INK, fontweight="bold", pad=26)
    ax.text(0, 1.03, "Categories are folded to the top "
            f"{len([c for c in chart_df.columns if c != 'Other'])} plus \"Other\" "
            "to keep the legend readable", transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=min(4, n_series),
              frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(TREND_PNG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
