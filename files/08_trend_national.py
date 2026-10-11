"""Step 8 (optional): chart how national PCE and inflation moved month to month.

Run:  python 08_trend_national.py

Writes output/trend_national.csv and output/trend_national.png.

Unlike the other charts in this project, this one has no "you" side - it's
purely the national numbers over the last year, for context on whether the
year you're comparing your own spending against was a normal one, a high-
inflation one, etc.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # save to file, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd

from pce_common import TREND_NATIONAL_CSV, TREND_NATIONAL_PNG, info, load_fred_trend

BLUE = "#2a78d6"
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
TARGET_LINE = "#c3c2b7"


def main() -> None:
    trend, meta = load_fred_trend()
    trend = trend.sort_values("date")
    trend.to_csv(TREND_NATIONAL_CSV, index=False, date_format="%Y-%m-%d")

    print(f"\nNational PCE and inflation, {trend['date'].min():%b %Y} to {trend['date'].max():%b %Y}\n")
    header = f"{'Month':<10}{'PCE ($B, SAAR)':>18}{'Inflation (YoY)':>18}"
    print(header)
    print("-" * len(header))
    for _, r in trend.iterrows():
        month_label = f"{r['date']:%b %Y}"
        print(f"{month_label:<10}{r['pce_billions']:>17,.0f} {r['yoy_pct']:>16.1f}%")
    print("-" * len(header))
    print(f"\nLatest ({meta['latest_month']}): ${meta['latest_pce_billions']:,.0f}B spending, "
          f"{meta['latest_inflation_yoy_pct']:.1f}% inflation (year over year)")
    print(f"Source: {meta['source']}")

    make_chart(trend)
    info(f"Saved {TREND_NATIONAL_CSV.name} and {TREND_NATIONAL_PNG.name} in the output folder")


def make_chart(trend: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), dpi=150, sharex=True)
    fig.patch.set_facecolor("white")

    x = trend["date"]

    # Panel 1: PCE spending level.
    ax1.set_facecolor("white")
    ax1.plot(x, trend["pce_billions"], color=BLUE, linewidth=2, marker="o", markersize=4, zorder=3)
    ax1.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("${x:,.0f}B"))
    ax1.tick_params(axis="y", colors=MUTED, labelsize=8.5)
    ax1.tick_params(axis="x", length=0, labelbottom=False)
    ax1.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax1.spines[side].set_visible(False)
    ax1.spines["bottom"].set_color(GRID)
    ax1.set_title("National PCE spending (annual rate)", loc="left", fontsize=12,
                  color=INK, fontweight="bold", pad=12)

    # Panel 2: inflation, year over year, with the Fed's 2% target as a reference line.
    ax2.set_facecolor("white")
    ax2.axhline(2.0, color=TARGET_LINE, linewidth=1.2, linestyle="--", zorder=2)
    ax2.text(x.iloc[0], 2.0, " Fed 2% target", fontsize=7.5, color=MUTED, va="bottom")
    ax2.plot(x, trend["yoy_pct"], color=BLUE, linewidth=2, marker="o", markersize=4, zorder=3)
    ax2.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
    ax2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=100, decimals=1))
    ax2.tick_params(axis="y", colors=MUTED, labelsize=8.5)
    ax2.tick_params(axis="x", colors=MUTED, labelsize=8.5, rotation=45)
    ax2.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax2.spines[side].set_visible(False)
    ax2.spines["bottom"].set_color(GRID)
    ax2.set_title("PCE inflation (year over year)", loc="left", fontsize=12,
                  color=INK, fontweight="bold", pad=12)

    fig.suptitle("How the US economy moved this year", x=0.01, ha="left", fontsize=14,
                 color=INK, fontweight="bold", y=0.99)
    fig.text(0.01, 0.005, "Source: Federal Reserve Bank of St. Louis (FRED), series PCE and PCEPI. "
             "The Fed's preferred inflation measure.", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(TREND_NATIONAL_PNG)
    plt.close(fig)


if __name__ == "__main__":
    main()
