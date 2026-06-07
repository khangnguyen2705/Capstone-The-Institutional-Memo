"""v2.1 — Full-period (2022-2026) daily-close panel from the order book.

Streams every row-group of orderbook.parquet, takes the last mid per (day, ticker),
and assembles a daily panel for all well-covered names. This is the multi-regime,
wide-universe data base for the v2 strategy.

Output: data/cache/panel_fullperiod.csv
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
PARQUET = os.path.join(HERE, "orderbook.parquet")
COLS = ["timestamp", "ticker", "l1_bid_px", "l1_ask_px"]
MIN_COV = 0.90          # keep names present on >=90% of days


def main():
    pf = pq.ParquetFile(PARQUET)
    parts = []
    for i in range(pf.num_row_groups):
        df = pf.read_row_group(i, columns=COLS).to_pandas()
        df["mid"] = 0.5 * (df["l1_bid_px"] + df["l1_ask_px"])
        df = df[df["mid"] > 0]
        df["date"] = df["timestamp"].dt.normalize()
        last = df.groupby(["date", "ticker"])["mid"].last().reset_index()
        parts.append(last)
        if (i + 1) % 25 == 0:
            print(f"  ...row-group {i+1}/{pf.num_row_groups}")
    alld = pd.concat(parts, ignore_index=True)
    # a (date,ticker) can appear in two adjacent groups; take the last
    alld = alld.groupby(["date", "ticker"])["mid"].last().reset_index()
    panel = alld.pivot(index="date", columns="ticker", values="mid").sort_index()
    cov = panel.notna().mean()
    panel = panel[cov[cov > MIN_COV].index].ffill().dropna()
    panel.to_csv(os.path.join(CACHE, "panel_fullperiod.csv"))
    print(f"[panel] {panel.shape[0]} days x {panel.shape[1]} names  "
          f"{panel.index.min().date()} -> {panel.index.max().date()}")
    print(f"[done] panel_fullperiod.csv")


if __name__ == "__main__":
    main()
