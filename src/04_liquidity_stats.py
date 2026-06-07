"""M2 — Per-name liquidity & market-impact calibration from orderbook.parquet.

The feed is quote-only (L1-L3 minute snapshots; NO trade prints / volume), so we
calibrate impact with quote-only estimators that are standard on a real desk:

  * half-spread (bps)        : (ask-bid)/2 / mid          -> cost to cross
  * book depth (shares, $)   : L1 and L1-L3 summed sizes  -> displayed liquidity
  * mid volatility (ann.)    : std of daily mid returns
  * Kyle's lambda ($/share)  : OFI-based price impact (Cont-Kukanov-Stoikov 2014)
                               regress dMid on Order-Flow-Imbalance -> price/share
  * ADV proxy (shares/day)   : depth-based liquidity proxy (LABELLED a proxy, since
                               the feed carries no executed volume)

Calibrated on 2022 (matches the strategy backtest window). Restricted to the 50
names the book actually trades. Output: data/cache/liquidity_stats.csv
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
PARQUET = os.path.join(HERE, "orderbook.parquet")
COLS = ["timestamp", "ticker", "l1_bid_px", "l1_bid_sz", "l1_ask_px", "l1_ask_sz",
        "l2_bid_sz", "l2_ask_sz", "l3_bid_sz", "l3_ask_sz"]


def target_universe(mode: str = "") -> list[str]:
    panel = pd.read_csv(os.path.join(CACHE, "panel_v2.csv"), index_col=0, nrows=1)
    names = set(panel.columns.tolist())
    if mode == "v2":                       # add the v2 Kalman basket legs
        comp = pd.read_csv(os.path.join(CACHE, "v2_basket.csv"))
        for p in comp["pair"]:
            names.update(p.split("/"))
    return sorted(names)


def load_book(targets: set[str], year_max: int | None = 2022) -> pd.DataFrame:
    """Load filtered quotes. year_max=2022 -> backtest window; None -> full history."""
    pf = pq.ParquetFile(PARQUET)
    chunks = []
    for i in range(pf.num_row_groups):
        df = pf.read_row_group(i, columns=COLS).to_pandas()
        if year_max is not None and df["timestamp"].min().year > year_max:
            break                                   # groups are time-ordered
        df = df[df["ticker"].isin(targets)]
        if year_max is not None:
            df = df[df["timestamp"].dt.year <= year_max]
        if len(df):
            chunks.append(df)
    out = pd.concat(chunks, ignore_index=True)
    print(f"[load] {len(out):,} rows, {out.ticker.nunique()} names, "
          f"{out.timestamp.min().date()} -> {out.timestamp.max().date()}")
    return out


def ofi_lambda(g: pd.DataFrame) -> float:
    """Kyle's lambda via Order-Flow-Imbalance (Cont-Kukanov-Stoikov).
    e_n = 1{Pb>=Pb_}·qb - 1{Pb<=Pb_}·qb_ - 1{Pa<=Pa_}·qa + 1{Pa>=Pa_}·qa_
    Regress dMid on e -> lambda (price move per share of net flow)."""
    pb, qb = g["l1_bid_px"].values, g["l1_bid_sz"].values
    pa, qa = g["l1_ask_px"].values, g["l1_ask_sz"].values
    mid = 0.5 * (pb + pa)
    pb_, qb_ = pb[:-1], qb[:-1]; pa_, qa_ = pa[:-1], qa[:-1]
    pb1, qb1 = pb[1:], qb[1:]; pa1, qa1 = pa[1:], qa[1:]
    e = ((pb1 >= pb_) * qb1 - (pb1 <= pb_) * qb_
         - (pa1 <= pa_) * qa1 + (pa1 >= pa_) * qa_)
    dmid = np.diff(mid)
    m = np.isfinite(e) & np.isfinite(dmid) & (e != 0)
    if m.sum() < 50:
        return np.nan
    lam = np.linalg.lstsq(e[m].reshape(-1, 1), dmid[m], rcond=None)[0][0]
    return float(lam) if lam > 0 else np.nan       # impact must be positive


def per_name(g: pd.DataFrame) -> dict:
    g = g.sort_values("timestamp")
    mid = 0.5 * (g["l1_bid_px"] + g["l1_ask_px"])
    half_spread_bps = ((g["l1_ask_px"] - g["l1_bid_px"]) / 2 / mid * 1e4).median()
    depth_top = (g["l1_bid_sz"] + g["l1_ask_sz"]).median() / 2          # avg side, shares
    depth_l123 = ((g["l1_bid_sz"] + g["l2_bid_sz"] + g["l3_bid_sz"]
                   + g["l1_ask_sz"] + g["l2_ask_sz"] + g["l3_ask_sz"]).median()) / 2
    px = mid.median()
    # daily mid-return vol -> annualized
    daily = mid.groupby(g["timestamp"].dt.date).last()
    dr = daily.pct_change().dropna()
    dr = dr[dr.abs() < 0.5]                     # drop split-day jumps (e.g. AMZN/GOOGL 20:1)
    sigma_ann = dr.std() * np.sqrt(252) if len(dr) > 5 else np.nan
    # ADV proxy (shares/day): mean over days of (summed top-of-book one-side depth)
    by_day = (g["l1_bid_sz"] + g["l1_ask_sz"]).groupby(g["timestamp"].dt.date).sum() / 2
    adv_proxy = by_day.mean()
    lam = ofi_lambda(g)
    return {"mid_px": px, "half_spread_bps": half_spread_bps,
            "depth_top_sh": depth_top, "depth_l123_sh": depth_l123,
            "sigma_ann": sigma_ann, "kyle_lambda_usd_per_sh": lam,
            "adv_proxy_sh": adv_proxy, "n_obs": len(g)}


def main():
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    full = mode in ("full", "v2")
    suffix = {"full": "_full", "v2": "_v2"}.get(mode, "")
    outname = f"liquidity_stats{suffix}.csv"
    targets = set(target_universe("v2" if mode == "v2" else ""))
    print(f"[universe] {len(targets)} target names  mode={mode or '2022'}")
    raw = load_book(targets, year_max=None if full else 2022)
    rows = {tk: per_name(g) for tk, g in raw.groupby("ticker")}
    out = pd.DataFrame(rows).T.sort_index()
    out.index.name = "ticker"
    # derived $ fields
    out["depth_top_usd"] = out["depth_top_sh"] * out["mid_px"]
    out["depth_l123_usd"] = out["depth_l123_sh"] * out["mid_px"]
    out["adv_proxy_usd"] = out["adv_proxy_sh"] * out["mid_px"]
    # bps of mid-move per $1k traded = lambda($/sh)/mid /mid *1000 *1e4
    out["lambda_bps_per_1k_usd"] = (out["kyle_lambda_usd_per_sh"]
                                    / out["mid_px"] ** 2 * 1000 * 1e4)
    n_nan = int(out["kyle_lambda_usd_per_sh"].isna().sum())
    print(f"[lambda] {n_nan}/{len(out)} names with NaN lambda (fallback to cross-sec median in M3)")
    out.to_csv(os.path.join(CACHE, outname))
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(out[["mid_px", "half_spread_bps", "depth_top_sh", "depth_l123_usd",
               "sigma_ann", "kyle_lambda_usd_per_sh", "adv_proxy_usd"]].round(4).to_string())
    print(f"\n[done] {len(out)} names -> {outname}")
    print(f"[summary] median half-spread={out.half_spread_bps.median():.2f} bps  "
          f"median depth(top,$)={out.depth_top_usd.median():,.0f}  "
          f"median lambda={out.kyle_lambda_usd_per_sh.median():.2e} $/sh")


if __name__ == "__main__":
    main()
