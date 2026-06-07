# Capstone — The Institutional Memo

> A hedge-fund-style **Capital Allocation Request**: a market-neutral systematic
> equity book, calibrated and sized the way a real execution desk would — with the
> **capacity question** ("how much can we trade before we ruin the spread?") as the
> centerpiece.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Status](https://img.shields.io/badge/build-reproducible-brightgreen)
![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)

**Deliverable:** [`INVESTMENT_MEMO.md`](INVESTMENT_MEMO.md) (also rendered to PDF and
Word). A 5-page institutional memo: strategy thesis → backtest → risk metrics →
**capacity / market-impact analysis** → the capital ask.

---

## What this is

The book funds a **cointegration-pairs + cross-sectional-momentum** blend
(dollar-neutral, market beta ≈ 0) — the only strategy that survived out-of-sample
validation with realistic frictions. The memo's distinguishing feature is a
**capacity analysis calibrated directly from L1–L3 order-book data**: per-name
half-spread, depth, mid-volatility, and **Kyle's λ** (order-flow-imbalance impact),
combined into a net-Sharpe-vs-capital frontier.

### Two tiers

- **v1 (base)** — 2022 walk-forward blend; OOS Sharpe 1.73; capacity calibrated on
  2022 vs full-period liquidity; conservative capital ask with staged deployment.
- **v2 (upgrade)** — full **2022–2026** history (1,064 days × 505 names), **Kalman
  time-varying hedge ratios**, wide-universe gated pairs, **Combinatorial Purged
  Cross-Validation** + **Deflated Sharpe**, and an **empirically tested** square-root
  impact law. Key finding: capacity is a function of **execution quality** — below
  ~25% spread capture the thin edge is consumed by the spread.

---

## Repository layout

```
.
├── INVESTMENT_MEMO.md / .pdf / .docx   # the deliverable
├── IMPLEMENTATION_PLAN.md              # institutional build plan
├── src/
│   ├── 03_blend_oos.py        # v1 strategy + OOS P&L
│   ├── 04_liquidity_stats.py  # impact calibration from the order book
│   ├── 05_capacity.py         # v1 capacity frontier
│   ├── 06_risk.py             # risk metrics + 1987 crash stress
│   ├── 07_capital_ask.py      # sizing the ask
│   ├── 08_sensitivity.py      # hurdle × fraction grid
│   ├── 10_panel_fullperiod.py # v2 full-history panel
│   ├── 11_strategy_v2.py      # v2 Kalman pairs + momentum + CPCV/DSR
│   ├── 12_empirical_impact.py # square-root-law test (23.5M obs)
│   ├── 13_capacity_v2.py      # v2 execution-quality capacity
│   └── 09_render.py           # markdown → PDF + Word
├── figures/                   # generated exhibits (PNG)
└── requirements.txt
```

> **Data is intentionally excluded.** The raw course datasets (order-book parquet,
> OHLC archives, minute flat files) and all derived market data are not distributed.
> The repository publishes the *methodology and results*, not a runnable copy.

---

## License

**All Rights Reserved — Proprietary.** See [`LICENSE`](LICENSE). This work is shown for
academic evaluation and portfolio review only; no permission is granted to copy, reuse,
or redistribute any part of it.
