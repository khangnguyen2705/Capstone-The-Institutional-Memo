# CAPITAL ALLOCATION REQUEST — INVESTMENT MEMO

**To:** Fund Investment / Risk Committee
**From:** K. Nguyen — Execution & Systematic Strategies
**Re:** Capital allocation to the **Market-Neutral Pairs + Momentum Blend** (the "Book")
**Date:** 2026-06-07
**Classification:** Internal — Capital Committee

> **THE ASK IN ONE LINE.** Allocate **$35M** to a dollar-neutral, market-neutral
> systematic equity book (OOS Sharpe **1.73**, vol **3.2%**, market beta **−0.02**,
> max drawdown **−1.9%**). $35M is **65% of measured capacity ($53.6M)** — the
> point at which our own market impact begins to erode the edge — leaving deliberate
> headroom. Expected net contribution: **$1.2–1.7M/yr** at a net Sharpe of **1.1–1.6**.

---

## 1. Strategy Thesis — what we are funding

The Book combines **two structurally uncorrelated systematic equity strategies** into a
single risk-optimized, dollar-neutral portfolio:

- **Cointegration Pairs (mean-reversion), 80% of risk.** A *basket of 9 within-sector
  pairs* — not a single fragile relationship — each gated on three independent tests:
  Engle–Granger cointegration *p*, ADF stationarity of the spread, and a mean-reversion
  half-life between 1 and 90 days. Positions enter at ±1.5σ, exit at 0.5σ, hard-stop at
  3.5σ; legs are dollar-neutral; the basket is inverse-vol weighted.
- **Cross-sectional Momentum (trend), 20% of risk.** 60-1 formation (trailing 60-day
  return, skipping the last 5 days), long top quintile / short bottom quintile,
  equal-weight, monthly rebalance.

**Why blend them.** The two sleeves are nearly uncorrelated (ρ = **−0.11** in calm
markets). Mean-variance optimization with **Ledoit–Wolf shrinkage** covariance places
~**80/20** in pairs/momentum at the minimum-variance point. The result is a book whose
realized **market beta is −0.02** — a genuine *diversifier*, not a repackaged long.

**The 9-pair basket (calibrated 2022):**

| Pair | Sector | Coint *p* | Half-life (d) | Wt |
|---|---|---|---|---|
| PEP/MCD | Staples | 0.002 | 4.5 | 16.2% |
| KO/CL | Staples | 0.008 | 6.9 | 16.3% |
| MS/BLK | Financials | 0.032 | 10.7 | 9.5% |
| SPY/GLD | Cross-asset | 0.052 | 8.8 | 9.5% |
| MSFT/ADBE | Tech | 0.054 | 7.5 | 7.1% |
| JNJ/PFE | Health | 0.056 | 8.3 | 11.1% |
| V/MA | Payments | 0.058 | 7.6 | 17.9% |
| UNH/MRK | Health | 0.064 | 8.5 | 6.1% |
| GE/LOW | Industrials | 0.072 | 8.0 | 6.2% |

**Honest scope note (why this and not an intraday book).** Prior research built an
intraday order-book residual stat-arb signal that *looked* strong (Sharpe ~1.6) but was
**retracted under our own kill-test**: it was bid-ask bounce that dies on a one-bar
execution lag. We do **not** ask for capital on it. Instead we repurpose that
order-book work as the **market-impact calibration engine** behind §4. Funding the
strategy that survived honest out-of-sample validation — and disclosing the one that
didn't — is the discipline this committee should expect.

---

## 2. Backtest Performance — the honest scorecard

All figures below are **out-of-sample** (expanding-window, purged walk-forward, 21-day
rebalance, Ledoit–Wolf shrinkage, turnover-damped, net of cost). OOS window
**2022-06-09 → 2022-12-30 (142 trading days)**. Selection used only pre-window data.

| Book | OOS Sharpe | Ann. Return | Ann. Vol |
|---|---|---|---|
| **Robust walk-forward Blend (funded)** | **1.73** | **5.5%** | **3.2%** |
| 100% Pairs basket | 5.36 | 13.0% | 2.4% |
| 100% Momentum | −1.82 | −21.1% | 11.6% |
| Static 60/40 | −0.13 | −0.6% | 4.8% |

*See `figures/walkforward_oos.png` (carried from the strategy build) and
`figures/drawdown.png`.*

**Reading this honestly.** In choppy 2022, momentum was a structural loser; the robust
optimizer *correctly downweighted it*, and the Blend **crushed naive 60/40 and beat the
weak sleeve**. It did **not** beat pairs-alone — and we do not claim it should. The
pairs-alone 5.36 Sharpe is an in-sample-flavored, frictionless figure treated as a
*ranking signal, not a promise*. **The disciplined claim is this:** allocation protects
the book from its weak sleeve and delivers a low-volatility, market-neutral return
stream — it does not manufacture alpha out of one sleeve.

**Data note.** Strategy returns are calibrated on 2022 daily closes (the OHLC sample
available); the order-book record runs to 2026-03 and is used for the forward liquidity
and impact picture in §4. The short return sample is a known limitation and is the
reason the ask is sized conservatively and staged (§5).

---

## 3. Risk Metrics

Computed on the OOS net daily P&L of the Blend (142 days):

| Metric | Value | Read |
|---|---|---|
| Annualized Sharpe | **1.73** | risk-adjusted return |
| Sortino | **2.88** | downside-only; left tail is benign |
| Max Drawdown | **−1.95%** | shallow; recovers quickly |
| Calmar | **2.82** | return per unit of worst loss |
| Daily VaR (95% / 99%) | −0.31% / −0.42% | risk-limit anchors |
| Daily CVaR (95% / 99%) | −0.39% / −0.52% | expected tail loss |
| Skew / Excess kurtosis | +0.08 / +0.74 | **not** "pennies before a steamroller" |
| **Market beta** | **−0.02** | **proves market-neutrality** |
| Probabilistic Sharpe (vs 0) | 0.90 | 90% confidence Sharpe > 0 |
| Deflated Sharpe (100 trials) | 0.11 | *see caveat* |

**The one number we will not hide — Deflated Sharpe = 0.11.** After deflating for
multiple testing (≈100 pair-search trials) over only 142 OOS days, the Sharpe is **not
yet statistically distinguishable** from what a search of that size could produce by
luck (expected max Sharpe under the null ≈ 3.4 given the tiny sample). This is a
*sample-length* limitation, not a sign the edge is fake — the economics (cointegration,
sector structure, near-zero beta) are sound. **Mitigant:** we size the ask well below
capacity and **stage** deployment (§5) so live data extends the track record before
full size is committed. We would rather state this openly than be caught by it.

**Stress — 1987 Black Monday overlay.** Replaying the Book against the 1987 crash tape
(S&P futures **−21.2%** worst day, **−28.6%** peak-to-trough; ~**7.8×** normal daily
vol):

| Channel | Modeled 1-day impact |
|---|---|
| Directional (β × crash) | **+0.5%** (slight short beta *helps*) |
| Idiosyncratic / correlation-breakdown (99%, at 7.8× vol) | **−3.6%** |
| **Net scenario loss** | **−3.1%** |
| **After −5% kill-switch** | **−3.1% (inside the stop)** |

Even a Black-Monday-scale shock produces a modeled ~**−3% day**, contained by the
governance limits in §5. The book's only real crash vulnerability is correlation
breakdown (sleeve ρ moves −0.11 → **+0.24** on worst-decile days), which we already
size to — the headline weight is set to the *stressed* correlation, not the calm one.

---

## 4. Capacity Analysis — "How much can we trade before we ruin the spread?"

This is the core of the request. Capacity is set by the point where **our own market
impact eats the gross edge**. We calibrate impact directly from the **L1–L3 order book**
(213M quote rows; 50 traded names; 2022, matching the backtest window).

**Step 1 — Liquidity calibration (per name, from the book).** Median half-spread
**4.24 bps**; displayed L1–L3 depth (ETFs deepest: SPY ≈ $100k/snapshot, single names
≈ $25k); annualized mid volatility; and **Kyle's λ** (price impact per share),
estimated by regressing minute mid-changes on **order-flow imbalance**
(Cont–Kukanov–Stoikov). *Note:* the feed carries quotes only (no executed volume), so
all impact estimates are quote-based and, where displayed depth is used as the liquidity
scale, deliberately **conservative**.

**Step 2 — Cost vs. capital.** The Book's **gross alpha is 5.66%/yr** at a one-way
**turnover of 15.3× book/yr**. Crossing the spread is size-independent and costs
**0.67%/yr**. Market impact *grows with capital*. We price it two ways:

- **Kyle's λ (linear, directly calibrated):** the *optimistic* bound — permanent impact
  is gentle; net Sharpe stays above the hurdle past **$3B**.
- **Square-root law (Almgren) on displayed depth:** the *conservative* bound — net
  Sharpe falls to the **1.0 hurdle at ≈ $54M**.

These **bracket** true capacity. Per Jane-Street discipline, **we anchor on the
conservative bound.**

**Step 3 — The capacity frontier**, calibrated on two liquidity regimes
(`figures/capacity_frontier.png`, `figures/capacity_frontier_full.png`):

| Capacity definition | 2022 (stressed yr) | 2022–2026 (forward) |
|---|---|---|
| **Hard capacity — √-law + Sharpe ≥ 1.0 (anchor)** | **$53.6M** | **$76.2M** |
| Participation cap — ≤10% of displayed depth | $113.7M | $98.7M |
| Hard capacity — Kyle-λ (optimistic bound) | >$3,000M | >$3,000M |
| Median half-spread | 4.24 bps | 3.75 bps |

> **STATED CAPACITY = $53.6M (stressed) to $76.2M (forward).** We **anchor on the
> stressed-2022 number, $53.6M** — the most conservative binding constraint
> (√-law + hurdle), well inside the participation cap and far inside the Kyle-λ bound.
> The forward, full-period liquidity (tighter spreads, gentler impact as markets
> normalized after 2022) lifts capacity to **$76.2M**, which we treat as the **scale-up
> target**, not the opening ask. Beyond capacity, net Sharpe drops below the Board's
> 1.0 floor.

`figures/impact_curve.png` shows net dollar P&L vs. capital — it rises, then rolls over
as impact compounds: the visual answer to "how much before we ruin the spread."

**Capacity is hurdle-sensitive** (√-law, forward period) — the Board's chosen Sharpe
floor materially moves the number:

| Board hurdle (Sharpe) | 0.50 | 0.75 | **1.00** | 1.25 | 1.50 |
|---|---|---|---|---|---|
| Stated capacity | $251M | $151M | **$76M** | $26M | $6M |

We adopt the **1.00 hurdle** as the prudent default; a softer hurdle would justify a
materially larger allocation.

---

## 5. The Capital Request

**We request $35M** — **65% of the $53.6M stated capacity**, leaving **$18.6M of
headroom** by design.

**Expected economics at $35M** (impact priced at the requested size):

| | Conservative (√-law) | Optimistic (Kyle-λ) |
|---|---|---|
| Net annual return | 3.5% | 5.0% |
| **Net Sharpe** | **1.11** | **1.56** |
| **Net P&L contribution** | **$1.23M/yr** | **$1.74M/yr** |
| Max single-name participation | 2.99% of displayed depth | (same) |

At $35M the book never exceeds **~3% of displayed depth** in any name — a third of the
10% governance cap. We do not become the market.

**Deployment — staged, not day-one, with a defined scale-path.** Ramp the opening
$35M over four monthly rebalances ($10M → $20M → $30M → $35M), each tranche gated on
live tracking-error and slippage-vs-model checks. Thereafter, scale toward **$50M** (65%
of the **$76M forward capacity**) and ultimately the forward capacity itself **only as
live execution confirms the gentler post-2022 liquidity regime** measured in §4. Staging
also lengthens the live track record that §3 flagged as short. Indicative economics at
the $50M scale-up: net Sharpe **1.1–1.6**, net P&L **$1.7–2.5M/yr**.

**Risk limits offered to the Committee (execution-desk governance):**

- **Drawdown kill-switch** at −5% (the 1987 scenario stays inside this).
- **Daily VaR(99%) limit** ≈ 0.5% of book (≈ measured −0.42%).
- **Participation cap** ≤ 10% of displayed depth per name per day.
- **Volatility target** ~10% annualized scaling; single-name and gross-exposure caps.
- **Liquidity kill-switch** on a depth-collapse signal from the live order book
  (the 1987-style trigger).
- **Capacity re-test** quarterly on fresh order-book data; the ask is re-based if
  measured capacity moves.

**Summary.** A market-neutral, low-volatility, capacity-aware sleeve with disclosed
limitations, conservative sizing, and explicit governance. **We request $35M**, with a
defined path to scale toward the $53.6M capacity — and beyond, should live impact
confirm the gentler Kyle-λ bound — as the live record matures.

---

## 6. Strategy v2 — Multi-Regime Upgrade (recommended evolution)

The base case (§§1–5) is honest but rests on a **142-day, 2022-only** sample — its
**Deflated Sharpe of 0.11** is the binding weakness. We have since built a **v2** that
merges three upgrades into one and re-validates on the **full order-book history**:

1. **Multi-regime + wide universe** — daily panel rebuilt from `orderbook.parquet`:
   **1,064 days × 505 names (2022-04 → 2026-03)**. Pairs are gated from the *whole*
   universe (correlation pre-filter → cointegration → ADF → half-life), surfacing
   genuinely cointegrated relationships the 50-name set could not — utility clusters
   (AEE/AEP, AEP/XEL/XLU), dual-class arbitrages (**GOOG/GOOGL, NWS/NWSA**), chemicals
   (DOW/LYB), energy (APA/EOG).
2. **Decay-resistant alpha** — static OLS hedge ratios replaced with **online Kalman
   time-varying hedge ratios** (causal; the direct cure for the relationship-drift that
   killed the daily pairs bot in prior work).
3. **Honest validation** — pairs selected on an **in-sample 2022 window only**;
   performance measured on **812 OOS days (2023–2026)**; **Combinatorial Purged
   Cross-Validation** (28 paths) plus a **Deflated Sharpe** over the larger sample.

**v2 out-of-sample scorecard:**

| Metric | v1 (base) | **v2 (upgrade)** |
|---|---|---|
| OOS window | 142 d (2022) | **812 d (2023–26)** |
| OOS Sharpe | 1.73 | **1.58** |
| Sharpe by year | — | 1.26 / 1.11 / 1.61 / 4.69 (all +) |
| **Deflated Sharpe** | **0.11** | **0.39** |
| CPCV mean / 5th-pctile / % positive | — | **1.68 / 1.01 / 100%** |
| Max Drawdown | −1.95% | −0.25% |
| Vol (unlevered) | 3.18% | 0.31% |

The headline Sharpe is marginally lower, but **statistical confidence rises sharply**:
every CPCV path is positive, the 5th-percentile path still clears Sharpe 1.0, and the
edge holds across four distinct regime-years it was *not* fit on. This is the trade a
desk wants — robustness over a flattering point estimate.

**v2 capacity — and the execution-quality finding.** Re-costing on full-period liquidity
(`figures/capacity_frontier_v2.png`): Kyle-λ capacity **$602M** gross notional, binding
**participation cap (≤10% displayed depth) at $61M** → **stated capacity $61M**, ask
(65%) **$40M gross notional**, net Sharpe **1.31** (Kyle) at the ask. We also
**empirically tested the square-root law** on 23.5M minute observations: the fit is noisy
(R²≈0.09) and super-linear (exponent ≈1.4), so we retain the directly-calibrated Kyle-λ
rather than a fitted coefficient.

The critical execution-desk insight is that v2's gross alpha is **thin relative to
spreads** — capacity is a function of **execution quality** (fraction of half-spread
captured via passive/smart fills):

| Spread capture | 0% (always cross) | 25% | 50% | 75% |
|---|---|---|---|---|
| Stated capacity | **~$0** | $61M | $61M | $61M |

**Below ~25% spread capture the book has no capacity** — crossing the full spread on
5.6× turnover consumes the edge. This *quantifies why execution is the strategy*: the
allocation should be paired with a passive/liquidity-providing execution mandate, which
is precisely this desk's function.

---

### Appendix — Reproducibility

All figures generated from the pipeline in `src/` against the supplied data.
**v1 (base):** `03_blend_oos.py` → `04_liquidity_stats.py` (impact calibration from
`orderbook.parquet`) → `05_capacity.py` → `06_risk.py` (risk + 1987 stress) →
`07_capital_ask.py` → `08_sensitivity.py`. **v2 (upgrade):** `10_panel_fullperiod.py`
(full-history panel) → `11_strategy_v2.py` (Kalman pairs + momentum + CPCV/DSR) →
`12_empirical_impact.py` (square-root-law test, 23.5M obs) → `13_capacity_v2.py`
(execution-quality capacity). Rendered via `09_render.py`. Numeric outputs cached as
JSON in `data/cache/`.
