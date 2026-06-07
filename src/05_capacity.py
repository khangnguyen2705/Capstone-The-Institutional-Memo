"""M3 — Capacity analysis: "How much can we trade before we ruin the spread?"

Builds the per-name traded-notional map of the book (80% pairs basket / 20%
momentum), then prices execution cost as a function of deployed capital A using
two impact models, and locates capacity.

Impact models
  (1) Kyle's lambda (PRIMARY) — directly calibrated from observed dMid vs OFI.
      Per daily clip v_i ($): impact_bps_i = 0.5 * lambda_i * (v_i/mid_i) / mid_i * 1e4
      -> linear in A -> net_return(A) = g - c_spread - c_impact * A.
  (2) Square-root law (CROSS-CHECK, Almgren) using DISPLAYED daily depth as the
      liquidity scale (the feed has no executed volume; displayed depth is a
      CONSERVATIVE proxy that understates true ADV, so it understates capacity).

Capacity points: hard (net Sharpe >= hurdle), economic (max net $ P&L),
zero-edge (net return = 0), and a 10%-of-displayed-depth participation cap.

Outputs: data/cache/capacity.json, figures/capacity_frontier.png,
         figures/impact_curve.png
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
os.makedirs(FIG, exist_ok=True)

HURDLE = 1.0           # Board Sharpe floor defining hard capacity
PARTICIPATION = 0.10   # max fraction of displayed daily depth per name per day
Y_SQRT = 0.5           # square-root-law coefficient (Almgren ~0.3-1)
W_PAIRS, W_MOM = 0.80, 0.20


def notional_weights(liq: pd.DataFrame) -> pd.Series:
    """Share of book notional carried by each name."""
    comp = pd.read_csv(os.path.join(CACHE, "basket_composition.csv"))
    w = pd.Series(0.0, index=liq.index, dtype=float)
    # pairs: each pair's inv-vol weight split 50/50 across its two legs
    for _, r in comp.iterrows():
        a, b = r["pair"].split("/")
        for leg in (a, b):
            if leg in w.index:
                w[leg] += W_PAIRS * r["inv_vol_w"] * 0.5
    # momentum: spread across the full traded universe
    uni = liq.index
    w[uni] += W_MOM / len(uni)
    return w / w.sum()


def main():
    import sys
    full = len(sys.argv) > 1 and sys.argv[1] == "full"
    suf = "_full" if full else ""
    liq = pd.read_csv(os.path.join(CACHE, f"liquidity_stats{suf}.csv"), index_col="ticker")
    sc = json.load(open(os.path.join(CACHE, "scorecard.json")))
    g = sc["gross_ann_return"]
    sigma = sc["books"]["OOS_walk_forward_blend"]["ann_vol"]
    tau = sc["ann_turnover_oneway"]                       # x book / yr, one-way
    lam_med = liq["kyle_lambda_usd_per_sh"].median()
    liq["lam"] = liq["kyle_lambda_usd_per_sh"].fillna(lam_med)

    w = notional_weights(liq)
    liq = liq.assign(w=w)
    sig_d = liq["sigma_ann"] / np.sqrt(252)              # daily vol per name

    # effective book half-spread (notional-weighted), annual spread drag
    eff_half_spread_bps = float((liq["w"] * liq["half_spread_bps"]).sum())
    c_spread = tau * eff_half_spread_bps / 1e4           # annual return drag, size-independent
    print(f"[inputs] g={g:.4%}  sigma={sigma:.4%}  turnover={tau:.1f}x/yr")
    print(f"[spread] eff half-spread={eff_half_spread_bps:.2f} bps  -> spread drag={c_spread:.4%}/yr")

    def costs_at(A):
        """Return (kyle_drag, sqrt_drag, max_participation) annual rates at AUM=A."""
        daily_clip = liq["w"] * (tau / 252.0) * A          # $ per name per day
        # (1) Kyle linear
        imp_bps_k = 0.5 * liq["lam"] * (daily_clip / liq["mid_px"]) / liq["mid_px"] * 1e4
        kyle = 252.0 * float((daily_clip * imp_bps_k / 1e4).sum()) / A
        # (2) sqrt-law on displayed daily depth proxy
        part = daily_clip / liq["adv_proxy_usd"]
        imp_bps_s = Y_SQRT * sig_d * np.sqrt(part.clip(lower=0)) * 1e4
        sqrtd = 252.0 * float((daily_clip * imp_bps_s / 1e4).sum()) / A
        return kyle, sqrtd, float(part.max())

    grid = np.linspace(1e6, 3e9, 400)
    net_k, net_s, netp_k, parts = [], [], [], []
    for A in grid:
        ck, cs, pmax = costs_at(A)
        nk = g - c_spread - ck
        net_k.append(nk); net_s.append(g - c_spread - cs)
        netp_k.append(nk * A); parts.append(pmax)
    net_k, net_s, netp_k, parts = map(np.array, (net_k, net_s, netp_k, parts))
    sharpe_k = net_k / sigma
    sharpe_s = net_s / sigma

    def cap_at_sharpe(sh, h):
        below = np.where(sh < h)[0]
        return float(grid[below[0]]) if len(below) else float(grid[-1])

    cap_hard_k = cap_at_sharpe(sharpe_k, HURDLE)
    cap_hard_s = cap_at_sharpe(sharpe_s, HURDLE)
    cap_zero_k = cap_at_sharpe(sharpe_k, 0.0)
    cap_econ_k = float(grid[int(np.argmax(netp_k))])
    cap_part = float(grid[np.where(parts <= PARTICIPATION)[0][-1]]) \
        if (parts <= PARTICIPATION).any() else float(grid[0])
    # Anchor on the most CONSERVATIVE binding constraint (do not overstate capacity).
    # Kyle-λ (permanent impact) is the optimistic bound; √-law on displayed depth +
    # the participation cap are the conservative ones.
    stated = min(cap_hard_s, cap_part)

    out = {
        "gross_ann_return": g, "ann_vol": sigma, "turnover_oneway": tau,
        "eff_half_spread_bps": round(eff_half_spread_bps, 3),
        "spread_drag_annual": round(c_spread, 5), "hurdle_sharpe": HURDLE,
        "capacity_hard_kyle_usd": round(cap_hard_k, 0),
        "capacity_hard_sqrt_usd": round(cap_hard_s, 0),
        "capacity_economic_kyle_usd": round(cap_econ_k, 0),
        "capacity_zero_edge_kyle_usd": round(cap_zero_k, 0),
        "capacity_participation_usd": round(cap_part, 0),
        "STATED_CAPACITY_usd": round(stated, 0),
    }
    with open(os.path.join(CACHE, f"capacity{suf}.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[capacity] mode={'FULL 2022-2026' if full else '2022'}")
    for k, v in out.items():
        if k.endswith("_usd"):
            print(f"   {k:34s} ${v/1e6:,.1f}M")
    print(f"\n[STATED CAPACITY] ${stated/1e6:,.0f}M  (min of hard-Sharpe & participation cap)")

    # ---- figure 1: capacity frontier (net Sharpe vs AUM) ----
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(grid / 1e6, sharpe_k, lw=2.6, color="#1f77b4", label="Net Sharpe — Kyle-λ impact (primary)")
    ax.plot(grid / 1e6, sharpe_s, lw=2.0, color="#9467bd", ls="--", label="Net Sharpe — √-law (depth proxy, conservative)")
    ax.axhline(HURDLE, color="#d62728", ls=":", lw=1.5, label=f"Board hurdle (Sharpe {HURDLE})")
    ax.axvline(stated / 1e6, color="#2ca02c", lw=2.0, alpha=.8, label=f"Stated capacity ≈ ${stated/1e6:,.0f}M")
    ax.set_xlabel("Deployed capital A ($M)"); ax.set_ylabel("Net annualized Sharpe")
    ax.set_title("Capacity Frontier — Net Sharpe vs. Deployed Capital\n"
                 "(market-neutral blend; impact calibrated from L1–L3 order book, 2022)")
    ax.set_ylim(-0.5, sharpe_k.max() * 1.05); ax.grid(alpha=.3); ax.legend(fontsize=8.5)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, f"capacity_frontier{suf}.png"), dpi=150)
    print(f"[plot] figures/capacity_frontier{suf}.png")

    # ---- figure 2: net $ P&L vs AUM (economic capacity) ----
    fig2, ax2 = plt.subplots(figsize=(9, 5.5))
    ax2.plot(grid / 1e6, netp_k / 1e6, lw=2.6, color="#1f77b4", label="Net P&L ($M/yr) — Kyle-λ")
    ax2.axvline(cap_econ_k / 1e6, color="#ff7f0e", lw=2.0, label=f"Economic capacity ≈ ${cap_econ_k/1e6:,.0f}M (max $ P&L)")
    ax2.axvline(stated / 1e6, color="#2ca02c", lw=2.0, alpha=.8, label=f"Stated capacity ≈ ${stated/1e6:,.0f}M")
    ax2.set_xlabel("Deployed capital A ($M)"); ax2.set_ylabel("Net annual P&L ($M)")
    ax2.set_title("Net Dollar P&L vs. Deployed Capital — the edge rolls over as impact compounds")
    ax2.grid(alpha=.3); ax2.legend(fontsize=8.5)
    fig2.tight_layout(); fig2.savefig(os.path.join(FIG, f"impact_curve{suf}.png"), dpi=150)
    print(f"[plot] figures/impact_curve{suf}.png")


if __name__ == "__main__":
    main()
