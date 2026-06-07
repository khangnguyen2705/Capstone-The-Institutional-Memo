"""v2.3a — Empirically TEST the square-root impact law from the order book.

Instead of assuming impact ~ Y*sigma*sqrt(participation) with Y=0.5, we fit the
EXPONENT and COEFFICIENT from the data:

  per minute, per name:  participation = |OFI| / book_depth   (signed flow / liquidity)
                         impact_bps    = |dMid| / mid * 1e4
  pooled log-log fit:    log(impact_bps) = c + alpha * log(participation)

alpha ~ 0.5 would CONFIRM the square-root law; the fitted (alpha, coef) then drive
the v2 capacity curve. Full-period, 50 traded names.

Output: data/cache/impact_fit.json
"""
from __future__ import annotations
import os, json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
PARQUET = os.path.join(HERE, "orderbook.parquet")
COLS = ["timestamp", "ticker", "l1_bid_px", "l1_bid_sz", "l1_ask_px", "l1_ask_sz",
        "l2_bid_sz", "l2_ask_sz", "l3_bid_sz", "l3_ask_sz"]


def targets():
    p = pd.read_csv(os.path.join(CACHE, "panel_v2.csv"), index_col=0, nrows=1)
    return set(p.columns)


def main():
    tk = targets()
    pf = pq.ParquetFile(PARQUET)
    part, imp = [], []
    for i in range(pf.num_row_groups):
        df = pf.read_row_group(i, columns=COLS).to_pandas()
        df = df[df["ticker"].isin(tk)]
        if not len(df):
            continue
        for _, g in df.groupby("ticker"):
            g = g.sort_values("timestamp")
            pb, qb = g["l1_bid_px"].values, g["l1_bid_sz"].values
            pa, qa = g["l1_ask_px"].values, g["l1_ask_sz"].values
            if len(g) < 5:
                continue
            mid = 0.5 * (pb + pa)
            depth = (g["l1_bid_sz"] + g["l2_bid_sz"] + g["l3_bid_sz"]
                     + g["l1_ask_sz"] + g["l2_ask_sz"] + g["l3_ask_sz"]).values / 2
            pb_, qb_ = pb[:-1], qb[:-1]; pa_, qa_ = pa[:-1], qa[:-1]
            pb1, qb1 = pb[1:], qb[1:]; pa1, qa1 = pa[1:], qa[1:]
            ofi = ((pb1 >= pb_) * qb1 - (pb1 <= pb_) * qb_
                   - (pa1 <= pa_) * qa1 + (pa1 >= pa_) * qa_)
            dmid_bps = np.abs(np.diff(mid)) / mid[:-1] * 1e4
            d = depth[1:]
            pr = np.abs(ofi) / np.where(d > 0, d, np.nan)
            m = np.isfinite(pr) & np.isfinite(dmid_bps) & (pr > 0) & (dmid_bps > 0)
            part.append(pr[m]); imp.append(dmid_bps[m])
        if (i + 1) % 50 == 0:
            print(f"  ...row-group {i+1}/{pf.num_row_groups}")
    P = np.concatenate(part); I = np.concatenate(imp)
    # clip extreme tails (robust)
    lo, hi = np.percentile(P, 1), np.percentile(P, 99)
    keep = (P >= lo) & (P <= hi)
    P, I = P[keep], I[keep]
    print(f"[fit] {len(P):,} pooled minute observations")
    x, y = np.log(P), np.log(I)
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    c, alpha = float(coef[0]), float(coef[1])
    yhat = A @ coef
    ss_res = float(((y - yhat) ** 2).sum()); ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    out = {
        "n_obs": int(len(P)), "exponent_alpha": round(alpha, 4),
        "intercept_c": round(c, 4), "coef_exp_c": round(float(np.exp(c)), 4),
        "r2": round(r2, 4),
        "interpretation": f"impact_bps ≈ {np.exp(c):.3f} * participation^{alpha:.3f}",
        "sqrt_law_alpha_ref": 0.5,
    }
    with open(os.path.join(CACHE, "impact_fit.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(f"\n[verdict] fitted exponent {alpha:.3f} vs square-root-law 0.5 "
          f"-> {'CONFIRMS' if 0.35 < alpha < 0.65 else 'DEVIATES from'} √-law")


if __name__ == "__main__":
    main()
