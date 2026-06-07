"""v2.3b — Capacity for the v2 book (Kalman pairs + momentum, full period).

Same impact framework as v1 (Kyle-λ primary, √-law conservative cross-check) but on
v2 economics (lower turnover 5.6x, full-period liquidity) and reporting capacity as
GROSS DEPLOYED NOTIONAL (the market footprint that determines impact). The empirical
exponent test (impact_fit.json) is reported as a diagnostic.

Outputs: data/cache/capacity_v2.json, data/cache/ask_v2.json,
         figures/capacity_frontier_v2.png
"""
from __future__ import annotations
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
FIG = os.path.join(HERE, "figures")

HURDLE, PARTICIPATION, Y_SQRT = 1.0, 0.10, 0.5
W_PAIRS, W_MOM = 0.977, 0.023            # v2 avg blend weights
TARGET_VOL = 0.08                         # vol-target for the capital-ask translation
FRACTION = 0.65
CAPTURE = 0.50      # fraction of half-spread CAPTURED via passive/smart execution
                    # (0 = always cross/pay; 1 = always provide/earn). 0.5 = realistic mix.
CAPTURE_GRID = [0.0, 0.25, 0.50, 0.75]


def main():
    liq = pd.read_csv(os.path.join(CACHE, "liquidity_stats_v2.csv"), index_col="ticker")
    sc = json.load(open(os.path.join(CACHE, "v2_scorecard.json")))
    fit = json.load(open(os.path.join(CACHE, "impact_fit.json")))
    g, sigma, tau = sc["gross_ann_return"], sc["ann_vol"], sc["ann_turnover_oneway"]
    lam = liq["kyle_lambda_usd_per_sh"].fillna(liq["kyle_lambda_usd_per_sh"].median())
    sig_d = liq["sigma_ann"] / np.sqrt(252)

    # v2 basket names -> notional weights (pairs dominate)
    comp = pd.read_csv(os.path.join(CACHE, "v2_basket.csv"))
    w = pd.Series(0.0, index=liq.index, dtype=float)
    in_book = [t for p in comp["pair"] for t in p.split("/") if t in w.index]
    # pairs legs present in our liquidity universe; spread pair weight, rest to momentum proxy
    for _, r in comp.iterrows():
        for leg in r["pair"].split("/"):
            if leg in w.index:
                w[leg] += W_PAIRS * r["inv_vol_w"] * 0.5
    w[liq.index] += W_MOM / len(liq.index)
    if w.sum() == 0:
        w[liq.index] = 1.0
    w = w / w.sum()
    eff_hs = float((w * liq["half_spread_bps"]).sum())

    def spread_drag(capture):
        return tau * eff_hs * (1 - capture) / 1e4

    def costs(A):
        clip = w * (tau / 252.0) * A
        imp_k = 0.5 * lam * (clip / liq["mid_px"]) / liq["mid_px"] * 1e4
        kyle = 252.0 * float((clip * imp_k / 1e4).sum()) / A
        part = clip / liq["adv_proxy_usd"]
        imp_s = Y_SQRT * sig_d * np.sqrt(part.clip(lower=0)) * 1e4
        sq = 252.0 * float((clip * imp_s / 1e4).sum()) / A
        return kyle, sq, float(part.max())

    grid = np.linspace(1e6, 5e9, 500)
    impact_k = np.array([costs(A)[0] for A in grid])
    impact_s = np.array([costs(A)[1] for A in grid])
    pa = np.array([costs(A)[2] for A in grid])

    def cap(sh, h):
        b = np.where(sh < h)[0]
        return float(grid[b[0]]) if len(b) else float(grid[-1])

    cap_p = float(grid[np.where(pa <= PARTICIPATION)[0][-1]]) if (pa <= PARTICIPATION).any() else grid[0]

    # capacity vs execution quality (spread capture) — the execution-desk lever.
    # Kyle-λ impact (directly calibrated), capped by the participation constraint.
    cap_by_capture = {}
    for cpt in CAPTURE_GRID:
        cd = spread_drag(cpt)
        shk_c = (g - cd - impact_k) / sigma
        cap_by_capture[f"{cpt:.2f}"] = round(min(cap(shk_c, HURDLE), cap_p), 0)

    c_spread = spread_drag(CAPTURE)
    nk = g - c_spread - impact_k
    ns = g - c_spread - impact_s
    shk, shs = nk / sigma, ns / sigma
    cap_k, cap_s = cap(shk, HURDLE), cap(shs, HURDLE)
    # Anchor on the participation cap (concrete, defensible), inside the Kyle-λ bound.
    # The √-law-on-displayed-depth pins low because the quote feed has no executed
    # volume (depth proxy understates true ADV); it is reported as an execution-risk
    # floor, not the capacity anchor.
    stated = min(cap_k, cap_p)
    ask = round(FRACTION * stated, -6)
    # economics at the ask
    ck, cs, pmax = costs(ask)
    out = {
        "basis": "GROSS DEPLOYED NOTIONAL (market footprint)",
        "gross_ann_return": g, "ann_vol_unlevered": sigma, "turnover_oneway": tau,
        "eff_half_spread_bps": round(eff_hs, 3),
        "spread_capture_assumed": CAPTURE, "spread_drag_annual": round(c_spread, 5),
        "capacity_by_spread_capture_usd": cap_by_capture,
        "empirical_impact_exponent": fit["exponent_alpha"], "empirical_impact_r2": fit["r2"],
        "capacity_hard_kyle_usd": round(cap_k, 0), "capacity_hard_sqrt_usd": round(cap_s, 0),
        "capacity_participation_usd": round(cap_p, 0), "STATED_CAPACITY_usd": round(stated, 0),
        "CAPITAL_ASK_usd": ask,
        "ask_net_sharpe_sqrt": round((g - c_spread - cs) / sigma, 2),
        "ask_net_sharpe_kyle": round((g - c_spread - ck) / sigma, 2),
        "ask_max_participation": round(pmax, 4),
        "target_vol_for_translation": TARGET_VOL,
        "implied_leverage_at_target_vol": round(TARGET_VOL / sigma, 1),
    }
    json.dump(out, open(os.path.join(CACHE, "capacity_v2.json"), "w"), indent=2)
    json.dump(out, open(os.path.join(CACHE, "ask_v2.json"), "w"), indent=2)
    print(json.dumps(out, indent=2))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(grid/1e6, shk, lw=2.6, color="#1f77b4", label="Net Sharpe — Kyle-λ (primary)")
    ax.plot(grid/1e6, shs, lw=2.0, color="#9467bd", ls="--", label="Net Sharpe — √-law (conservative)")
    ax.axhline(HURDLE, color="#d62728", ls=":", lw=1.5, label=f"Hurdle (Sharpe {HURDLE})")
    ax.axvline(stated/1e6, color="#2ca02c", lw=2, label=f"Stated capacity ≈ ${stated/1e6:,.0f}M")
    ax.axvline(ask/1e6, color="#ff7f0e", lw=2, ls="-.", label=f"Ask ≈ ${ask/1e6:,.0f}M")
    ax.set_xlabel("Gross deployed notional ($M)"); ax.set_ylabel("Net annualized Sharpe")
    ax.set_title("v2 Capacity Frontier — Kalman book, full-period liquidity\n"
                 "(Sharpe leverage-invariant; capacity = gross market footprint)")
    ax.set_ylim(-0.5, max(2.0, shk.max()*1.05)); ax.grid(alpha=.3); ax.legend(fontsize=8.5)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "capacity_frontier_v2.png"), dpi=150)
    print("[plot] figures/capacity_frontier_v2.png")
    print(f"\n[v2 ASK] ${ask/1e6:,.0f}M gross notional  "
          f"(={FRACTION:.0%} of ${stated/1e6:,.0f}M)  "
          f"net Sharpe {out['ask_net_sharpe_sqrt']}-{out['ask_net_sharpe_kyle']}")


if __name__ == "__main__":
    main()
