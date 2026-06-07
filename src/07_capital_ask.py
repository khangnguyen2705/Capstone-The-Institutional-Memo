"""M5 — Size the capital ask and compute expected economics at the requested size.

Ask = 65% of stated (conservative) capacity, leaving headroom. Reports expected
net return / Sharpe / $ P&L at the requested size under BOTH impact models.

Output: data/cache/ask.json
"""
from __future__ import annotations
import os, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")

FRACTION = 0.65          # request this fraction of stated capacity
Y_SQRT, W_PAIRS, W_MOM = 0.5, 0.80, 0.20


def main():
    import sys
    full = len(sys.argv) > 1 and sys.argv[1] == "full"
    suf = "_full" if full else ""
    cap = json.load(open(os.path.join(CACHE, f"capacity{suf}.json")))
    sc = json.load(open(os.path.join(CACHE, "scorecard.json")))
    liq = pd.read_csv(os.path.join(CACHE, f"liquidity_stats{suf}.csv"), index_col="ticker")
    comp = pd.read_csv(os.path.join(CACHE, "basket_composition.csv"))

    g, sigma, tau = cap["gross_ann_return"], cap["ann_vol"], cap["turnover_oneway"]
    c_spread = cap["spread_drag_annual"]
    stated = cap["STATED_CAPACITY_usd"]
    ask = round(FRACTION * stated, -6)             # round to nearest $1M

    # rebuild notional weights (same as M3)
    w = pd.Series(0.0, index=liq.index, dtype=float)
    for _, r in comp.iterrows():
        a, b = r["pair"].split("/")
        for leg in (a, b):
            if leg in w.index:
                w[leg] += W_PAIRS * r["inv_vol_w"] * 0.5
    w[liq.index] += W_MOM / len(liq.index)
    w = w / w.sum()
    lam = liq["kyle_lambda_usd_per_sh"].fillna(liq["kyle_lambda_usd_per_sh"].median())
    sig_d = liq["sigma_ann"] / np.sqrt(252)

    def net_at(A):
        clip = w * (tau / 252.0) * A
        imp_k = 0.5 * lam * (clip / liq["mid_px"]) / liq["mid_px"] * 1e4
        kyle = 252.0 * float((clip * imp_k / 1e4).sum()) / A
        part = clip / liq["adv_proxy_usd"]
        imp_s = Y_SQRT * sig_d * np.sqrt(part.clip(lower=0)) * 1e4
        sqrtd = 252.0 * float((clip * imp_s / 1e4).sum()) / A
        nk, ns = g - c_spread - kyle, g - c_spread - sqrtd
        return nk, ns, float(part.max())

    nk, ns, pmax = net_at(ask)
    out = {
        "stated_capacity_usd": stated,
        "request_fraction": FRACTION,
        "CAPITAL_ASK_usd": ask,
        "at_ask": {
            "net_return_kyle": round(nk, 4), "net_sharpe_kyle": round(nk / sigma, 2),
            "net_return_sqrt": round(ns, 4), "net_sharpe_sqrt": round(ns / sigma, 2),
            "expected_net_pnl_kyle_usd": round(nk * ask, 0),
            "expected_net_pnl_sqrt_usd": round(ns * ask, 0),
            "max_name_participation": round(pmax, 4),
            "ann_vol": sigma, "headroom_to_capacity_usd": round(stated - ask, 0),
        },
    }
    with open(os.path.join(CACHE, f"ask{suf}.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(f"\n[ASK] ${ask/1e6:,.0f}M  (={FRACTION:.0%} of ${stated/1e6:,.0f}M stated capacity)")
    print(f"      expected net Sharpe {ns/sigma:.2f} (√-law) to {nk/sigma:.2f} (Kyle)")
    print(f"      expected net P&L ${ns*ask/1e6:,.1f}M (√-law) to ${nk*ask/1e6:,.1f}M (Kyle)")


if __name__ == "__main__":
    main()
