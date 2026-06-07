# Implementation Plan — Week 11 Capstone

## Capital Allocation Request to the Fund Board

**Author:** Quant Research / Execution — K. Nguyen
**Role on hand-in:** Execution Trader (capacity & market-impact owner)
**Date:** 2026-06-07
**Status:** Plan → build → memo
**Deliverable:** 5-page Investment Memo, delivered as paste-in Markdown (+ Python as fenced blocks / `.ipynb`)

---

## 0. Mandate & framing

This is **not** a backtest report. A Capital Allocation Request is a *risk-adjusted promise* to a
Board: "Allocate **\$X**, and this book returns **\$Y** at volatility **\$Z** — and here is the exact
capital level at which my own trading destroys the edge." On an execution desk the memo is won or
lost in **§4 Capacity**: anyone can curve-fit a Sharpe; the differentiated skill is knowing your own
market-impact decay curve and stating it honestly.

**Intellectual-honesty constraint (carried from Week 9).** Every positive figure must survive a
kill-test. Frictionless / in-sample numbers are labelled as *ranking signals*, never promises. The
headline ask is sized to the **net-of-impact** curve, not the paper backtest.

---

## 1. Strategy thesis — what we are funding (Memo §1)

**We capitalize the Week-10 Robust Walk-Forward Blend** — the *only* strategy across the program that
survived out-of-sample validation with frictions. It combines two structurally uncorrelated
systematic equity books:

| Sleeve | Construction (locked from Week 10) |
|---|---|
| **Cointegration Pairs** (mean-reversion) | Engle–Granger on log prices; OLS hedge ratio; rolling z-score; enter ±1.5σ, exit 0.5σ, hard stop 3.5σ; dollar-neutral; **basket of 9 within-sector pairs** gated by cointegration *p*, ADF stationarity, and mean-reversion half-life; inverse-vol combined |
| **Cross-sectional Momentum** (trend) | 60-1 formation (trailing 60d return, skip last 5d); long top quintile / short bottom quintile; equal-weight; monthly rebalance; daily MTM; dollar-neutral |
| **Allocation** | Mean-variance (`PyPortfolioOpt`), **Ledoit–Wolf shrinkage** covariance, expanding-window walk-forward, 21-day rebalance, turnover-damped, net of cost |

**The thesis the Board buys:** the two sleeves are nearly uncorrelated (ρ ≈ 0.05 calm), so blended
vol (~8.5%) sits *below* the weighted average of standalone vols (~11.6%) — diversification made
visible. The book is **market-neutral** (dollar-neutral both sleeves), so the return stream is a
genuine diversifier to a long-biased fund.

**Honest scope note (the differentiator).** Our intraday order-book residual strategy (Week 9 IFR)
showed Sharpe ~1.6 but was *retracted* — it was bid-ask bounce that dies on a 1-bar execution lag.
We do **not** ask for capital on it. We deploy it instead as the **execution/impact calibration
layer** (below). This is the right use of that work and it strengthens, not weakens, the ask.

> Decision required from PM: confirm we fund the **daily blend** (recommended) vs. attempting to
> resurrect an intraday book. Plan assumes the blend.

---

## 2. Data inventory (grounded in what is actually in the folder)

| File | Size | Role in this build |
|---|---|---|
| `orderbook.parquet` | 4.4 GB · **212,975,144 rows** · 204 row-groups | **Impact calibration.** Schema: `timestamp, ticker, l1_bid_px, l1_bid_sz, l1_ask_px, l1_ask_sz, l2_*, l3_*` (L1–L3 minute quotes, ~477 names, 2022-01-03 → 2026-03-19). Drives spread, depth, Kyle's λ. |
| `ohlc-2022-01.zip` … `ohlc-2022-12.zip` | ~40–75 MB each | **Strategy returns.** Per-ticker intraday OHLC → daily close panel → the two sleeves' return streams. |
| `one-minute-stock-flat-files.zip.zip` | 3.5 GB | Optional finer-grain bars for robustness / intraday cost checks. |
| `1987_crash_market_data.csv` | (in `../Khang EWY_Week 9/`) | **Tail stress overlay.** Liquidity-evaporation scenario for risk §3 and the kill-switch in §5. |

**Engineering notes.** `orderbook.parquet` is too large for memory — process **row-group by
row-group** (204 groups) or filter by `ticker`/date with `pyarrow` predicate pushdown. Cache derived
per-name liquidity stats (median spread, top-of-book depth, ADV proxy) to a small CSV so downstream
steps never re-scan 213M rows.

---

## 3. Architecture & build phases

```
data/  (raw zips + parquet, untouched)
  └─ cache/                # small derived artifacts, committed
src/
  ├─ 01_build_panel.py     # ohlc zips      -> daily close panel (reuse Week 10)
  ├─ 02_build_sleeves.py   # panel          -> pairs + momentum return streams
  ├─ 03_blend_oos.py       # sleeves        -> robust walk-forward blended P&L  (Memo §2,§3)
  ├─ 04_liquidity_stats.py # orderbook.parquet -> per-name spread/depth/ADV/λ  (Memo §4)
  ├─ 05_capacity.py        # blend + liquidity -> impact curve + capacity frontier (Memo §4)
  ├─ 06_risk.py            # blended P&L + 1987 -> Sharpe/Sortino/DD/VaR/stress (Memo §3)
  └─ 07_capital_ask.py     # capacity + hurdle -> sizing, limits, the ask       (Memo §5)
figures/                   # PNGs referenced by the memo
INVESTMENT_MEMO.md         # the 5-page deliverable (paste-in)
```

Reuse Week-10 `build_panel.py` / `build_sleeves.py` / `enhanced_strategy.py` wholesale — do **not**
rewrite the alpha. Week 11's *new* code is phases 04–07 (the execution/capacity contribution).

---

## 4. Backtest performance (Memo §2)

**Engine = the Week-10 robust harness, re-run and reported cleanly.**

- Expanding-window **purged + embargoed walk-forward** (no train→test leakage), 21-day rebalance.
- **Gross vs. net** reported side-by-side: gross (frictionless) and net (after the §4 cost model at
  the requested size). The *net* curve is the one the ask is built on.
- True OOS window **2025-01 → 2026-03** reported separately; never used for tuning.
- Outputs: equity curve, daily P&L series, ann. return, turnover, hit rate, P&L per unit turnover.

**Reference scorecard to reproduce / update (Week 10 OOS):**

| Book | OOS Sharpe | Ann. Return | Ann. Vol |
|---|---|---|---|
| Robust walk-forward blend | **1.73** | 5.5% | 3.2% |
| Static 60/40 | −0.13 | −0.6% | 4.8% |
| 100% Momentum | −1.82 | −21.1% | 11.6% |

> The blend *beats naive 60/40 and the weak sleeve but does not beat pairs-alone* — that honest
> framing stays in the memo. Disciplined allocation protects against weak sleeves; it does not
> manufacture alpha.

---

## 5. Risk metrics (Memo §3)

Computed from the **net** daily P&L series of the blend:

| Metric | Definition | Board use |
|---|---|---|
| **Sharpe** (ann.) | mean/std × √252 | risk-adjusted return; gate |
| **Sortino** | downside-deviation denominator | left-tail penalty |
| **Max Drawdown** + duration | peak-to-trough, recovery time | sizing & stop governance |
| **Calmar** | ann. return / \|MaxDD\| | |
| **VaR / CVaR (95/99%)** | historical + Cornish-Fisher | risk-limit setting |
| **Skew / kurtosis** | distribution shape | "pennies in front of a steamroller?" test |
| **Market beta** | regress vs. equal-weight universe | *proves* the §1 neutrality claim |
| **Deflated Sharpe (DSR)** | Sharpe adjusted for #trials, skew, length | multiple-testing honesty (Week 9 method) |

**Stress (the differentiator).** Replay the blend's exposures against `1987_crash_market_data.csv`:
quantify P&L under a one-day liquidity-evaporation/gap scenario, and show how the §5 kill-switch
caps it. Also re-estimate sleeve correlation on the **worst-decile market days** (Week 10 found ρ
moves −0.11 calm → +0.24 stressed) — size to the *tail* correlation, not the calm one.

---

## 6. Capacity analysis — THE CENTERPIECE (Memo §4, ~1.5 pages)

This answers **"What is your capacity? How much can you trade before you ruin the spread?"** with
real microstructure, not a hand-wave. Execution-trader emphasis ⇒ this section is the largest.

**(a) Calibrate impact from `orderbook.parquet`.** For each traded name compute, from L1–L3:
- median **half-spread** `s = (ask − bid)/2 / mid`,
- **top-of-book + L1–L3 depth** (`Σ sizes`) — the available liquidity per quote,
- an **ADV proxy** (depth × quote frequency, or from the minute files),
- **Kyle's λ** — regress short-horizon mid-price change on signed order-flow imbalance:
  `Δmid = λ · (signed volume) + ε`. λ is the price moved per unit traded.

**(b) Square-root impact law.** Fit / apply `impact_bps ≈ Y · σ · √(Q / ADV)` where `Q` = order
size, `σ` = name vol, `Y` ≈ O(1) calibrated constant. Cross-check that the √-law and the Kyle-λ
linear model agree at small size (they should, locally).

**(c) Edge-vs-impact break-even.** Per-trade **gross edge is ~constant** (from §2, in bps); impact
**grows with size**. Capacity is where, per trade:

```
gross edge (bps)  ≤  half-spread crossed  +  impact(Q)  +  fees
```

**(d) The capacity frontier.** Sweep deployed capital and plot **net P&L and net Sharpe vs. AUM** —
it rises, peaks, then rolls over as impact compounds. Report two numbers:
- **Hard capacity** = AUM where net Sharpe falls below the Board hurdle (e.g. 1.0).
- **Economic capacity** = AUM at peak *net P&L* (max dollar edge).

**(e) Participation cap.** Independently constrain each clip to ≤ **5–10% of ADV** so we never
*become* the market. Final stated capacity = `min(break-even capacity, participation-cap capacity)`.

**Headline output:** "**Net Sharpe stays ≥ [hurdle] up to \$[X]M; edge rolls over beyond \$[X]M.**"
plus the impact-decay chart and the capacity-frontier chart.

---

## 7. Capital request (Memo §5)

- **The ask:** request **60–70% of estimated hard capacity** — leaves headroom, signals discipline.
- **Use of capital + ramp schedule:** scale in over N rebalances, not full-size day one.
- **Expected return at requested size:** the **net-of-impact** number from §6 (not the frictionless
  backtest).
- **Risk limits offered to the Board (execution-desk governance):**
  - max drawdown stop (kill-switch), VaR(99%) limit,
  - per-name & gross participation caps (≤ X% ADV),
  - vol target (e.g. 10% ann.), single-name concentration cap,
  - **liquidity kill-switch** triggered on a 1987-style depth-collapse signal from the order book.

---

## 8. Memo assembly & format

- Deliverable = **`INVESTMENT_MEMO.md`**, ~5 pages, paste-in Markdown for the submission boxes.
- Charts embedded as referenced PNGs in `figures/` and described inline (so it reads even as plain
  text).
- Page budget tuned to the **Execution-Trader** role:

| § | Section | Page weight |
|---|---|---|
| 1 | Thesis | 0.5 |
| 2 | Backtest (gross vs. net) | 0.75 |
| 3 | Risk metrics + stress | 0.5 |
| **4** | **Capacity / market impact** | **1.75 (showcase)** |
| 5 | Capital ask + limits | 0.5 |
| — | Exhibits / appendix | 1.0 |

- Python included as fenced code blocks and/or a runnable `.ipynb`.

---

## 9. Build sequence (milestones)

1. **M1 — Reproduce the blend.** Run Week-10 phases 01–03 against the Week-11 OHLC zips → confirm
   the OOS scorecard (Sharpe ~1.73). *Gate: numbers reproduce.*
2. **M2 — Liquidity stats.** Phase 04 over `orderbook.parquet` (row-group streaming) → per-name
   spread / depth / ADV / Kyle's λ cache. *Gate: λ and spreads sane vs. known liquid names.*
3. **M3 — Capacity model.** Phase 05 → impact curve + capacity frontier + headline number.
4. **M4 — Risk + stress.** Phase 06 → full metrics table + 1987 stress P&L.
5. **M5 — Sizing.** Phase 07 → the ask, ramp, limits.
6. **M6 — Memo.** Assemble `INVESTMENT_MEMO.md` *from generated numbers* (no hand-keyed figures).

---

## 10. Open questions / inputs needed from PM/Board

1. **Strategy confirm:** fund the daily robust blend (recommended) — yes/no.
2. **Capital scale:** is there a course-assumed fund AUM / book size? If not, default to a stated
   institutional anchor (e.g. \$50–100M fund, this book one sleeve) and derive capacity bottom-up.
3. **Board hurdle:** Sharpe floor that defines "hard capacity" (default 1.0).
4. **Fee/borrow assumptions:** commission bps + short borrow — default to conservative (e.g. 1 bp
   per unit turnover, as Week 10) unless specified.

*Plan proceeds on the defaults above unless overridden.*

---

## 11. Risks to the deliverable (honest register)

- **Capacity rests on impact calibration.** λ/√-law fits are noisy on thin names — restrict the
  tradable universe to names with robust L1–L3 depth; report capacity with a confidence band.
- **OHLC = 2022 only for sleeves; order book runs to 2026.** Sleeve return history is one year by
  necessity (documented in Week 10) — frame Sharpe accordingly and lean on the order book for the
  *forward* liquidity picture.
- **Small net Sharpe (1.73 at 3.2% vol).** The honest pitch is *diversification + capacity*, not a
  flashy return — position the ask as a low-vol, market-neutral, capacity-aware sleeve.
```
