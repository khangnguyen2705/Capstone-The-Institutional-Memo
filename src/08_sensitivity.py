"""(c) Sensitivity — stated capacity vs Board hurdle, and capital ask vs request
fraction. Uses the conservative (√-law) impact model on full-period liquidity.

Output: data/cache/sensitivity.json  + printed Markdown tables for the memo.
"""
from __future__ import annotations
import os, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
Y_SQRT, W_PAIRS, W_MOM = 0.5, 0.80, 0.20
HURDLES = [0.50, 0.75, 1.00, 1.25, 1.50]
FRACTIONS = [0.50, 0.60, 0.65, 0.70]


def main():
    suf = "_full"
    liq = pd.read_csv(os.path.join(CACHE, f"liquidity_stats{suf}.csv"), index_col="ticker")
    sc = json.load(open(os.path.join(CACHE, "scorecard.json")))
    comp = pd.read_csv(os.path.join(CACHE, "basket_composition.csv"))
    g, sigma, tau = sc["gross_ann_return"], \
        sc["books"]["OOS_walk_forward_blend"]["ann_vol"], sc["ann_turnover_oneway"]

    w = pd.Series(0.0, index=liq.index, dtype=float)
    for _, r in comp.iterrows():
        a, b = r["pair"].split("/")
        for leg in (a, b):
            if leg in w.index:
                w[leg] += W_PAIRS * r["inv_vol_w"] * 0.5
    w[liq.index] += W_MOM / len(liq.index)
    w = w / w.sum()
    sig_d = liq["sigma_ann"] / np.sqrt(252)
    eff_hs = float((w * liq["half_spread_bps"]).sum())
    c_spread = tau * eff_hs / 1e4

    grid = np.linspace(1e6, 3e9, 600)

    def net_sharpe_sqrt(A):
        clip = w * (tau / 252.0) * A
        part = clip / liq["adv_proxy_usd"]
        imp = Y_SQRT * sig_d * np.sqrt(part.clip(lower=0)) * 1e4
        drag = 252.0 * float((clip * imp / 1e4).sum()) / A
        return (g - c_spread - drag) / sigma

    sh = np.array([net_sharpe_sqrt(A) for A in grid])

    def cap_for(h):
        below = np.where(sh < h)[0]
        return float(grid[below[0]]) if len(below) else float(grid[-1])

    caps = {h: cap_for(h) for h in HURDLES}
    table = {f"{h:.2f}": {f"{fr:.2f}": round(fr * caps[h], -6) for fr in FRACTIONS}
             for h in HURDLES}

    out = {"model": "sqrt-law, full-period 2022-2026", "capacity_by_hurdle_usd":
           {f"{h:.2f}": round(c, 0) for h, c in caps.items()},
           "ask_grid_usd": table}
    with open(os.path.join(CACHE, "sensitivity.json"), "w") as f:
        json.dump(out, f, indent=2)

    print("Capacity by Board hurdle (√-law, full-period):")
    print("| Hurdle Sharpe | Stated capacity |")
    print("|---|---|")
    for h in HURDLES:
        print(f"| {h:.2f} | ${caps[h]/1e6:,.0f}M |")
    print("\nCapital ask = fraction x capacity ($M):")
    hdr = "| Hurdle \\ Fraction | " + " | ".join(f"{int(fr*100)}%" for fr in FRACTIONS) + " |"
    print(hdr); print("|" + "---|" * (len(FRACTIONS) + 1))
    for h in HURDLES:
        cells = " | ".join(f"${fr*caps[h]/1e6:,.0f}M" for fr in FRACTIONS)
        print(f"| {h:.2f} | {cells} |")


if __name__ == "__main__":
    main()
