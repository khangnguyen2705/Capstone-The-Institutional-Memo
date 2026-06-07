"""M4 — Risk metrics + 1987 Black-Monday stress overlay.

Reads the OOS blended net P&L (data/cache/blend_oos_pnl.csv) and produces the
full Board risk table, then stresses the book against the 1987 crash tape.

Outputs: data/cache/risk.json, figures/drawdown.png
"""
from __future__ import annotations
import os, json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "data", "cache")
FIG = os.path.join(HERE, "figures")
AF = 252


def psr(sr_ann, r, sr_bench=0.0):
    """Probabilistic Sharpe Ratio vs benchmark (annualized inputs)."""
    n = len(r)
    sr = sr_ann / np.sqrt(AF)                      # de-annualize
    sb = sr_bench / np.sqrt(AF)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    denom = np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(stats.norm.cdf((sr - sb) * np.sqrt(n - 1) / denom))


def deflated_sr(sr_ann, r, n_trials):
    """Deflated Sharpe: PSR vs the Sharpe expected from the best of N trials."""
    n = len(r)
    sr = sr_ann / np.sqrt(AF)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    emc = 0.5772156649
    z = stats.norm.ppf(1 - 1.0 / n_trials) * (1 - emc) + \
        stats.norm.ppf(1 - 1.0 / n_trials * np.e ** -1) * emc
    sr0_var = (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    sr0 = z * np.sqrt(sr0_var / (n - 1))           # expected max Sharpe (per-period) under null
    denom = np.sqrt(sr0_var)
    return float(stats.norm.cdf((sr - sr0) * np.sqrt(n - 1) / denom)), float(sr0 * np.sqrt(AF))


def main():
    r = pd.read_csv(os.path.join(CACHE, "blend_oos_pnl.csv"), index_col=0,
                    parse_dates=True).iloc[:, 0]
    sc = json.load(open(os.path.join(CACHE, "scorecard.json")))

    mean_a, vol_a = r.mean() * AF, r.std() * np.sqrt(AF)
    sharpe = mean_a / vol_a
    downside = r[r < 0].std() * np.sqrt(AF)
    sortino = mean_a / downside if downside > 0 else np.nan
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    maxdd = float(dd.min())
    calmar = mean_a / abs(maxdd) if maxdd < 0 else np.nan
    var95 = float(np.percentile(r, 5)); var99 = float(np.percentile(r, 1))
    cvar95 = float(r[r <= var95].mean()); cvar99 = float(r[r <= var99].mean())
    skew = float(stats.skew(r)); kurt = float(stats.kurtosis(r, fisher=True))

    # market beta (vs SPY from the panel, over the OOS window)
    panel = pd.read_csv(os.path.join(CACHE, "panel_v2.csv"), index_col=0, parse_dates=True)
    proxy = "SPY" if "SPY" in panel else ("IWM" if "IWM" in panel else None)
    mkt = (panel[proxy].pct_change() if proxy else panel.pct_change().mean(axis=1)).reindex(r.index).fillna(0.0)
    beta = float(np.cov(r, mkt)[0, 1] / np.var(mkt)) if mkt.var() > 0 else 0.0

    psr0 = psr(sharpe, r.values)
    n_trials = 100                                  # ~within-sector pair combos scanned
    dsr, sr0 = deflated_sr(sharpe, r.values, n_trials)

    # ---------------- 1987 Black-Monday stress ----------------
    c87 = pd.read_csv(os.path.join(CACHE, "1987_crash_market_data.csv"), parse_dates=["Timestamp"])
    sp = pd.to_numeric(c87["SP500_Futures"], errors="coerce").dropna()
    sp.index = c87.loc[sp.index, "Timestamp"]
    daily = sp.groupby(sp.index.date).last()
    crash_daily_ret = daily.pct_change().dropna()
    worst_day = float(crash_daily_ret.min())                 # Black Monday daily move
    peak_trough = float(sp.min() / sp.cummax().max() - 1)    # intraday peak->trough
    crash_dvol = float(crash_daily_ret.std())

    # Scenario P&L on a MARKET-NEUTRAL book:
    # (1) residual directional hit = beta * crash move
    directional = beta * worst_day
    # (2) correlation-breakdown / idiosyncratic gap: 1-day 99% loss under STRESSED vol.
    #     stressed daily vol scaled by crash/normal vol ratio of the market.
    norm_dvol = float(mkt.std())
    stress_mult = crash_dvol / norm_dvol if norm_dvol > 0 else 5.0
    stressed_daily_vol = (vol_a / np.sqrt(AF)) * stress_mult
    idio_99 = -2.33 * stressed_daily_vol
    scenario_loss = directional + idio_99
    # (3) kill-switch: hard DD stop halts the book; cap the cumulative bleed.
    dd_stop = -0.05
    capped_loss = max(scenario_loss, dd_stop)

    out = {
        "window": f"{r.index[0].date()} -> {r.index[-1].date()}", "n_days": int(len(r)),
        "ann_return": round(mean_a, 4), "ann_vol": round(vol_a, 4),
        "sharpe": round(sharpe, 3), "sortino": round(sortino, 3),
        "max_drawdown": round(maxdd, 4), "calmar": round(calmar, 3),
        "VaR95_daily": round(var95, 5), "VaR99_daily": round(var99, 5),
        "CVaR95_daily": round(cvar95, 5), "CVaR99_daily": round(cvar99, 5),
        "skew": round(skew, 3), "excess_kurtosis": round(kurt, 3),
        "market_beta": round(beta, 4),
        "PSR_vs_0": round(psr0, 4), "deflated_SR": round(dsr, 4),
        "DSR_n_trials": n_trials, "expected_max_SR_under_null": round(sr0, 3),
        "stress_1987": {
            "crash_worst_day_ret": round(worst_day, 4),
            "crash_peak_to_trough": round(peak_trough, 4),
            "crash_vol_multiple": round(stress_mult, 1),
            "scenario_directional": round(directional, 5),
            "scenario_idio_99": round(idio_99, 5),
            "scenario_total_loss": round(scenario_loss, 5),
            "kill_switch_stop": dd_stop,
            "loss_after_kill_switch": round(capped_loss, 5),
        },
    }
    with open(os.path.join(CACHE, "risk.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))

    # drawdown figure
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    cum.plot(ax=a1, color="#1f77b4", lw=2.2)
    a1.set_title(f"OOS Blended Book — Growth of $1 & Drawdown  "
                 f"(Sharpe {sharpe:.2f}, MaxDD {maxdd:.1%})")
    a1.set_ylabel("Growth of $1"); a1.grid(alpha=.3)
    a2.fill_between(dd.index, dd.values * 100, 0, color="#d62728", alpha=.4)
    a2.set_ylabel("Drawdown (%)"); a2.grid(alpha=.3); a2.set_xlabel("")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "drawdown.png"), dpi=150)
    print("[plot] figures/drawdown.png")


if __name__ == "__main__":
    main()
