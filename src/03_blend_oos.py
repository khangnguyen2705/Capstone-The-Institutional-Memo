"""M1 — Reproduce the Week-10 Robust Walk-Forward Blend and persist its net P&L.

Self-contained: reads the cached daily close panel (data/cache/panel_v2.csv),
rebuilds the gated pairs basket + cross-sectional momentum sleeves, runs the
purged expanding-window walk-forward with Ledoit-Wolf shrinkage + turnover
damping, and writes the OUT-OF-SAMPLE net daily P&L series the rest of the
capacity/risk pipeline consumes.

Outputs (data/cache/):
  sleeve_returns.csv      Pairs, Momentum aligned daily returns
  basket_composition.csv  chosen pairs, coint p, half-life, inverse-vol weight
  blend_oos_pnl.csv       OOS blended net daily return (THE book P&L)
  scorecard.json          Sharpe / ann.ret / ann.vol for blend & benchmarks
"""
from __future__ import annotations
import os, json, itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint, adfuller
import statsmodels.api as sm
from pypfopt import expected_returns, risk_models, EfficientFrontier
from pypfopt.risk_models import CovarianceShrinkage

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
os.makedirs(CACHE, exist_ok=True)

SECTORS = {
    "TECH":   ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AVGO", "ADBE", "CRM"],
    "FIN":    ["JPM", "BAC", "GS", "MS", "C", "WFC", "AXP", "BLK"],
    "STAPLE": ["KO", "PEP", "PG", "WMT", "COST", "MCD", "MDLZ", "CL"],
    "ENERGY": ["XOM", "CVX", "COP", "SLB"],
    "HEALTH": ["JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY"],
    "INDDIS": ["CAT", "HON", "GE", "HD", "LOW", "NKE", "DIS"],
    "PAYMNT": ["V", "MA"],
    "ETF":    ["SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "GLD"],
}


def half_life(spread: pd.Series) -> float:
    s = spread.dropna()
    lag = s.shift(1).dropna()
    ds = (s - s.shift(1)).dropna()
    lag, ds = lag.align(ds, join="inner")
    b = sm.OLS(ds, sm.add_constant(lag)).fit().params.iloc[1]
    return -np.log(2) / b if b < 0 else np.inf


def pair_return(prices, a, b, z_win=30, entry=1.5, exit=0.5, stop=3.5, cost=1.0,
                return_turnover=False):
    la, lb = np.log(prices[a]), np.log(prices[b])
    beta = sm.OLS(la, sm.add_constant(lb)).fit().params.iloc[1]
    spread = la - beta * lb
    z = (spread - spread.rolling(z_win).mean()) / spread.rolling(z_win).std()
    pos = pd.Series(0.0, index=z.index); st = 0.0
    for t in range(1, len(z)):
        zt = z.iloc[t]
        if np.isnan(zt):
            pos.iloc[t] = 0.0; continue
        if st == 0.0:
            if zt > entry: st = -1.0
            elif zt < -entry: st = 1.0
        elif abs(zt) < exit or abs(zt) > stop:
            st = 0.0
        pos.iloc[t] = st
    gross = pos.shift(1) * spread.diff()
    turn = pos.diff().abs().fillna(0.0)
    ret = ((gross - cost / 1e4 * turn) / (1 + abs(beta))).fillna(0.0)
    if return_turnover:
        return ret, (turn / (1 + abs(beta))).fillna(0.0)
    return ret


def pairs_basket(prices, max_pairs=10, coint_max=0.08, adf_max=0.15, hl_lo=1.0, hl_hi=90.0):
    cand = []
    for sec, members in SECTORS.items():
        avail = [t for t in members if t in prices.columns]
        for a, b in itertools.combinations(avail, 2):
            la, lb = np.log(prices[a]), np.log(prices[b])
            try:
                _, cp, _ = coint(la, lb)
            except Exception:
                continue
            beta = sm.OLS(la, sm.add_constant(lb)).fit().params.iloc[1]
            spread = la - beta * lb
            ap = adfuller(spread.dropna())[1]
            hl = half_life(spread)
            if cp < coint_max and ap < adf_max and hl_lo < hl < hl_hi:
                cand.append((cp, sec, a, b, hl))
    cand.sort(key=lambda x: x[0])
    chosen = cand[:max_pairs]
    rets, turns = {}, {}
    for _, _, a, b, _ in chosen:
        r, t = pair_return(prices, a, b, return_turnover=True)
        rets[f"{a}/{b}"], turns[f"{a}/{b}"] = r, t
    R = pd.DataFrame(rets); T = pd.DataFrame(turns)
    iv = 1.0 / R.std().replace(0, np.nan)
    iv = (iv / iv.sum()).fillna(0.0)
    basket = (R * iv).sum(axis=1); basket.name = "Pairs"
    basket_turn = (T * iv).sum(axis=1)             # book-fraction traded per day
    comp = pd.DataFrame([(f"{a}/{b}", sec, cp, hl, iv[f"{a}/{b}"])
                         for cp, sec, a, b, hl in chosen],
                        columns=["pair", "sector", "coint_p", "half_life_d", "inv_vol_w"])
    return basket, comp, basket_turn


def momentum_sleeve(prices, lookback=60, skip=5, rebal=21, cost_bps=1.0,
                    return_turnover=False):
    rets = prices.pct_change()
    signal = prices.shift(skip) / prices.shift(lookback) - 1.0
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    cur = pd.Series(0.0, index=prices.columns)
    n = prices.shape[1]; k = max(1, n // 5)
    for i, dt in enumerate(prices.index):
        if i >= lookback and i % rebal == 0:
            s = signal.loc[dt].dropna()
            if len(s) >= 2 * k:
                ranked = s.sort_values()
                longs, shorts = ranked.index[-k:], ranked.index[:k]
                cur = pd.Series(0.0, index=prices.columns)
                cur[longs] = 0.5 / k; cur[shorts] = -0.5 / k
        weights.loc[dt] = cur
    gross = (weights.shift(1) * rets).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    ret = (gross - cost_bps / 1e4 * turnover).fillna(0.0); ret.name = "Momentum"
    if return_turnover:
        return ret, turnover
    return ret


def min_var_weight(S):
    ef = EfficientFrontier(pd.Series(0.0, index=S.columns), S, weight_bounds=(0, 1))
    ef.min_volatility()
    return ef.clean_weights()


def sharpe(x):
    return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0


def main():
    prices = pd.read_csv(os.path.join(CACHE, "panel_v2.csv"), index_col=0, parse_dates=True)
    print(f"[panel] {prices.shape[0]} days x {prices.shape[1]} tickers")

    pairs, comp, pairs_turn = pairs_basket(prices)
    mom, mom_turn = momentum_sleeve(prices, return_turnover=True)
    comp.to_csv(os.path.join(CACHE, "basket_composition.csv"), index=False)
    print(f"[basket] {len(comp)} pairs:\n{comp.to_string(index=False)}")

    R = pd.concat([pairs, mom], axis=1).dropna()
    R.columns = ["Pairs", "Momentum"]
    R = R.loc[(R != 0).any(axis=1).idxmax():]
    R.to_csv(os.path.join(CACHE, "sleeve_returns.csv"))
    Tn = pd.concat([pairs_turn, mom_turn], axis=1).reindex(R.index).fillna(0.0)
    Tn.columns = ["Pairs", "Momentum"]
    corr = R["Pairs"].corr(R["Momentum"])
    print(f"[align] {len(R)} days  corr={corr:.3f}")

    # stressed correlation (worst-decile market days)
    proxy = "SPY" if "SPY" in prices else ("IWM" if "IWM" in prices else None)
    mkt = (prices[proxy].pct_change() if proxy else prices.pct_change().mean(axis=1)).reindex(R.index)
    stress_days = R.index[mkt <= mkt.quantile(0.10)]
    S_stress = risk_models.sample_cov(R.loc[stress_days], returns_data=True, frequency=252)
    corr_stress = S_stress.iloc[0, 1] / np.sqrt(S_stress.iloc[0, 0] * S_stress.iloc[1, 1])

    # walk-forward OOS, Ledoit-Wolf, turnover-damped
    warm, hold, theta, cost = 60, 21, 0.5, 1.0
    w0 = min_var_weight(CovarianceShrinkage(R.iloc[:warm], returns_data=True,
                                            frequency=252).ledoit_wolf())
    w_prev = np.array([w0["Pairs"], w0["Momentum"]])
    oos = pd.Series(0.0, index=R.index)
    weight_path = []
    for t0 in range(warm, len(R), hold):
        train = R.iloc[:t0]
        S_tr = CovarianceShrinkage(train, returns_data=True, frequency=252).ledoit_wolf()
        w_new = min_var_weight(S_tr)
        w_tgt = np.array([w_new["Pairs"], w_new["Momentum"]])
        w_app = (1 - theta) * w_prev + theta * w_tgt
        turn = np.abs(w_app - w_prev).sum()
        seg = R.iloc[t0:t0 + hold]
        seg_ret = (seg.values @ w_app)
        if len(seg_ret):
            seg_ret[0] -= cost / 1e4 * turn
        oos.iloc[t0:t0 + hold] = seg_ret
        weight_path.append((str(R.index[t0].date()), float(w_app[0]), float(w_app[1])))
        w_prev = w_app
    oos = oos.iloc[warm:]
    oos.name = "blend_oos_net"
    oos.to_csv(os.path.join(CACHE, "blend_oos_pnl.csv"))

    bench = {
        "OOS_walk_forward_blend": oos,
        "Pairs_only": R["Pairs"].iloc[warm:],
        "Momentum_only": R["Momentum"].iloc[warm:],
        "Static_60_40": (0.6 * R["Pairs"] + 0.4 * R["Momentum"]).iloc[warm:],
    }
    # book turnover & gross alpha over the OOS window (book-fraction traded per year)
    avg_w_pairs = float(np.mean([w[1] for w in weight_path]))
    avg_w_mom = float(np.mean([w[2] for w in weight_path]))
    blend_turn = (avg_w_pairs * Tn["Pairs"] + avg_w_mom * Tn["Momentum"]).iloc[warm:]
    ann_turnover = float(blend_turn.mean() * 252)               # x book / year (one-way)
    # gross alpha = net + placeholder cost (1bp/turnover) added back
    gross_daily = oos + 1.0 / 1e4 * blend_turn.reindex(oos.index).fillna(0.0)
    gross_ann_return = float(gross_daily.mean() * 252)

    scorecard = {"corr_calm": float(corr), "corr_stress": float(corr_stress),
                 "avg_weight_pairs": avg_w_pairs, "avg_weight_mom": avg_w_mom,
                 "ann_turnover_oneway": round(ann_turnover, 3),
                 "gross_ann_return": round(gross_ann_return, 4),
                 "oos_start": str(oos.index[0].date()), "oos_end": str(oos.index[-1].date()),
                 "n_oos_days": int(len(oos)), "books": {}}
    print("\n[oos] annualized (out-of-sample window):")
    for k, v in bench.items():
        s, r, vol = sharpe(v), v.mean() * 252, v.std() * np.sqrt(252)
        scorecard["books"][k] = {"sharpe": round(float(s), 3),
                                 "ann_return": round(float(r), 4),
                                 "ann_vol": round(float(vol), 4)}
        print(f"      {k:24s} Sharpe={s:5.2f}  ann.ret={r:7.2%}  ann.vol={vol:6.2%}")
    print(f"\n[corr] calm={corr:.2f}  stressed={corr_stress:.2f}")

    with open(os.path.join(CACHE, "scorecard.json"), "w") as f:
        json.dump(scorecard, f, indent=2)
    print(f"\n[done] wrote blend_oos_pnl.csv ({len(oos)} days), scorecard.json")


if __name__ == "__main__":
    main()
