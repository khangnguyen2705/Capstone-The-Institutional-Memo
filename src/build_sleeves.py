"""Step 2 — Build the two STRATEGY return streams (the 'assets' for the frontier).

  Pairs sleeve     : daily cointegration mean-reversion on the best pair.
  Momentum sleeve  : cross-sectional 60-1 long/short on the daily panel.

Both are dollar-neutral long/short books, marked daily. We export each as a
daily return series so Week 10 can treat them as two assets in PyPortfolioOpt.

Outputs: data/pairs_returns.csv, data/momentum_returns.csv
"""
from __future__ import annotations
import os, itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm

from build_panel import build_panel, DATA

# Candidate economically-linked pairs (subset that survives the panel filter is used)
PAIR_CANDIDATES = [
    ("KO", "PEP"), ("V", "MA"), ("XOM", "CVX"), ("GS", "MS"),
    ("HD", "LOW"), ("XLF", "XLK"), ("JPM", "BAC"), ("AAPL", "MSFT"),
    ("PG", "CL"), ("MRK", "PFE"),
]


# ----------------------------------------------------------------------------- pairs
def best_pair(prices: pd.DataFrame) -> tuple[str, str]:
    """Pick the most cointegrated pair. Try the economically-linked candidates
    first; if none clears the 5% Engle-Granger threshold, scan every combination
    in the panel and take the lowest p-value."""
    best, best_p = None, 1.0
    for a, b in PAIR_CANDIDATES:
        if a in prices and b in prices:
            _, pval, _ = coint(np.log(prices[a]), np.log(prices[b]))
            if pval < best_p:
                best, best_p = (a, b), pval
    if best_p > 0.05:
        for a, b in itertools.combinations(prices.columns, 2):
            _, pval, _ = coint(np.log(prices[a]), np.log(prices[b]))
            if pval < best_p:
                best, best_p = (a, b), pval
    print(f"[pairs] selected {best} (coint p={best_p:.4f})")
    return best


def pairs_sleeve(prices: pd.DataFrame, z_win: int = 30, entry: float = 1.5,
                 exit: float = 0.5, stop: float = 3.5, cost_bps: float = 1.0) -> pd.Series:
    a, b = best_pair(prices)
    la, lb = np.log(prices[a]), np.log(prices[b])
    beta = sm.OLS(la, sm.add_constant(lb)).fit().params.iloc[1]
    spread = la - beta * lb
    z = (spread - spread.rolling(z_win).mean()) / spread.rolling(z_win).std()

    # Build position in spread units: -1 when rich (z>entry), +1 when cheap (z<-entry)
    pos = pd.Series(0.0, index=z.index)
    state = 0.0
    for t in range(1, len(z)):
        zt = z.iloc[t]
        if np.isnan(zt):
            pos.iloc[t] = 0.0
            continue
        if state == 0.0:
            if zt > entry:
                state = -1.0
            elif zt < -entry:
                state = 1.0
        else:
            if abs(zt) < exit or abs(zt) > stop:
                state = 0.0
        pos.iloc[t] = state

    # Spread daily change -> P&L of a unit-notional spread position; halve gross
    # so leg notionals (1 and beta) sum to ~1 -> comparable scale to momentum.
    dspread = spread.diff()
    gross = pos.shift(1) * dspread
    turnover = pos.diff().abs().fillna(0.0)
    ret = (gross - cost_bps / 1e4 * turnover) / (1 + abs(beta))
    ret = ret.fillna(0.0)
    ret.name = "Pairs"
    print(f"[pairs] ann.ret={ret.mean()*252:.3%}  ann.vol={ret.std()*np.sqrt(252):.3%}  "
          f"trades={(turnover>0).sum()}")
    return ret


# -------------------------------------------------------------------------- momentum
def momentum_sleeve(prices: pd.DataFrame, lookback: int = 60, skip: int = 5,
                    rebal: int = 21, cost_bps: float = 1.0) -> pd.Series:
    """Cross-sectional momentum: rank trailing (lookback-skip) return, long top
    quintile / short bottom quintile, equal-weight, monthly rebalance, daily MTM."""
    rets = prices.pct_change()
    signal = prices.shift(skip) / prices.shift(lookback) - 1.0  # 60-1 momentum

    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    cur = pd.Series(0.0, index=prices.columns)
    n = prices.shape[1]
    k = max(1, n // 5)  # quintile
    for i, dt in enumerate(prices.index):
        if i >= lookback and i % rebal == 0:
            s = signal.loc[dt].dropna()
            if len(s) >= 2 * k:
                ranked = s.sort_values()
                longs, shorts = ranked.index[-k:], ranked.index[:k]
                cur = pd.Series(0.0, index=prices.columns)
                cur[longs] = 0.5 / k          # +$0.5 long book
                cur[shorts] = -0.5 / k        # -$0.5 short book  (dollar-neutral)
        weights.loc[dt] = cur

    gross = (weights.shift(1) * rets).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    ret = (gross - cost_bps / 1e4 * turnover).fillna(0.0)
    ret.name = "Momentum"
    print(f"[mom]   ann.ret={ret.mean()*252:.3%}  ann.vol={ret.std()*np.sqrt(252):.3%}")
    return ret


def build_sleeves() -> pd.DataFrame:
    prices = build_panel()
    pairs = pairs_sleeve(prices)
    mom = momentum_sleeve(prices)
    R = pd.concat([pairs, mom], axis=1).dropna()
    # Trim warm-up zeros so both sleeves are live
    R = R.loc[(R != 0).any(axis=1).idxmax():]
    R["Pairs"].to_csv(os.path.join(DATA, "pairs_returns.csv"))
    R["Momentum"].to_csv(os.path.join(DATA, "momentum_returns.csv"))
    print(f"[sleeves] {R.shape[0]} aligned days  corr={R['Pairs'].corr(R['Momentum']):.3f}")
    return R


if __name__ == "__main__":
    R = build_sleeves()
    print(R.describe())
