"""Step 1 — Build a daily close panel from the monthly OHLC zips.

Each monthly zip (ohlc-2022-MM.zip) holds one CSV per ticker per trading day
with intraday minute bars: columns [ticker, volume, open, close, high, low,
window_start (ns epoch), transactions]. We take the LAST bar's close as the
daily close and the bar date as the index.

Output: data/daily_close_panel.csv  (rows = dates, cols = tickers)
"""
from __future__ import annotations
import zipfile, glob, os, time
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# Focused, liquid universe: large caps across sectors + core ETFs.
# Breadth is enough for decile/quintile momentum sorts; the named pairs
# candidates (KO/PEP, V/MA, XOM/CVX, GS/MS, HD/LOW, XLF/XLK) live here.
UNIVERSE = [
    # ETFs
    "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "GLD",
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AVGO", "ADBE", "CRM",
    # Financials
    "JPM", "BAC", "GS", "MS", "C", "WFC", "AXP", "BLK",
    # Staples
    "KO", "PEP", "PG", "WMT", "COST", "MCD", "MDLZ", "CL",
    # Energy
    "XOM", "CVX", "COP", "SLB",
    # Healthcare
    "JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY",
    # Industrials / discretionary
    "CAT", "HON", "GE", "HD", "LOW", "NKE", "DIS",
    # Payments
    "V", "MA",
]


def epoch_ns_to_date(ns: int) -> pd.Timestamp:
    return pd.Timestamp(ns, unit="ns", tz="UTC").tz_convert("America/New_York").normalize().tz_localize(None)


def build_panel() -> pd.DataFrame:
    cache = os.path.join(DATA, "daily_close_panel.csv")
    if os.path.exists(cache):
        print(f"[panel] cache hit -> {cache}")
        return pd.read_csv(cache, index_col=0, parse_dates=True)

    uni = set(UNIVERSE)
    records: list[tuple] = []  # (date, ticker, close)
    zips = sorted(glob.glob(os.path.join(HERE, "ohlc-2022-*.zip")))
    print(f"[panel] {len(zips)} monthly zips, universe={len(uni)} tickers")
    t0 = time.time()
    for zp in zips:
        with zipfile.ZipFile(zp) as z:
            names = [n for n in z.namelist() if n.endswith(".csv")]
            for n in names:
                tk = n.split("/")[-1].split("_")[0]
                if tk not in uni:
                    continue
                df = pd.read_csv(z.open(n), usecols=["close", "window_start"])
                if df.empty:
                    continue
                last = df.iloc[-1]
                records.append((epoch_ns_to_date(int(last["window_start"])), tk, float(last["close"])))
        print(f"[panel]   {os.path.basename(zp)} done  ({time.time()-t0:.1f}s)")

    long = pd.DataFrame(records, columns=["date", "ticker", "close"])
    panel = long.pivot_table(index="date", columns="ticker", values="close").sort_index()
    # Drop tickers with too many gaps, forward-fill small holes
    keep = panel.columns[panel.notna().mean() > 0.95]
    panel = panel[keep].ffill().dropna()
    panel.to_csv(cache)
    print(f"[panel] {panel.shape[0]} days x {panel.shape[1]} tickers -> {cache}")
    return panel


if __name__ == "__main__":
    p = build_panel()
    print(p.tail(3).iloc[:, :6])
