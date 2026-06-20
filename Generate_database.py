"""
Generates the Database JSON files from instance definitions.
Usage: python3 generate_database.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path(__file__).parent / "Database"
OUTPUT_DIR.mkdir(exist_ok=True)

END_DATE = pd.Timestamp("2026-01-01")
N_DAYS = 252  # ~1 year of business days
DATES = pd.bdate_range(end=END_DATE, periods=N_DAYS)


def generate_price_path(
    start_price: float, daily_vol: float, drift: float, seed: int
) -> list[float]:
    """Generates a price path via a simple geometric random walk (for realistic test data)."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=drift, scale=daily_vol, size=N_DAYS)
    prices = start_price * np.cumprod(1 + returns)
    return [round(p, 2) for p in prices]


def timeserie_to_dict(prices: list[float]) -> dict:
    """Serializes a Timeserie into a JSON-compatible dict (Date as ISO string)."""
    return {
        "Date": [d.strftime("%Y-%m-%d") for d in DATES],
        "Price": prices,
    }


# ---------------------------------------------------------------------------
# COMMODITIES (10 instances)
# ---------------------------------------------------------------------------
COMMODITIES_DEFS = [
    {"name": "Crude Oil", "start_price": 80.0, "daily_vol": 0.018, "drift": 0.0002},
    {"name": "Brent Oil", "start_price": 83.0, "daily_vol": 0.018, "drift": 0.0001},
    {"name": "Natural Gas", "start_price": 2.80, "daily_vol": 0.030, "drift": -0.0003},
    {"name": "Gold", "start_price": 1950.0, "daily_vol": 0.009, "drift": 0.0004},
    {"name": "Silver", "start_price": 24.0, "daily_vol": 0.015, "drift": 0.0003},
    {"name": "Copper", "start_price": 3.85, "daily_vol": 0.013, "drift": 0.0001},
    {"name": "Corn", "start_price": 4.70, "daily_vol": 0.014, "drift": 0.0000},
    {"name": "Wheat", "start_price": 6.20, "daily_vol": 0.016, "drift": -0.0001},
    {"name": "Soybeans", "start_price": 13.40, "daily_vol": 0.013, "drift": 0.0001},
    {"name": "Live Hogs", "start_price": 0.78, "daily_vol": 0.020, "drift": 0.0002},
]

commodities = {}
for i, c in enumerate(COMMODITIES_DEFS):
    prices = generate_price_path(
        c["start_price"], c["daily_vol"], c["drift"], seed=100 + i
    )
    commodities[c["name"]] = {
        "name": c["name"],
        "spot_prices": timeserie_to_dict(prices),
    }

with open(OUTPUT_DIR / "commodities.json", "w") as f:
    json.dump(commodities, f, indent=2)


# ---------------------------------------------------------------------------
# STOCKS (10 instances)
# ---------------------------------------------------------------------------
STOCKS_DEFS = [
    {"name": "AAPL", "start_price": 185.0, "daily_vol": 0.016, "drift": 0.0006},
    {"name": "MSFT", "start_price": 370.0, "daily_vol": 0.015, "drift": 0.0006},
    {"name": "GOOGL", "start_price": 140.0, "daily_vol": 0.017, "drift": 0.0005},
    {"name": "AMZN", "start_price": 150.0, "daily_vol": 0.019, "drift": 0.0005},
    {"name": "TSLA", "start_price": 240.0, "daily_vol": 0.035, "drift": 0.0002},
    {"name": "NVDA", "start_price": 480.0, "daily_vol": 0.030, "drift": 0.0010},
    {"name": "META", "start_price": 330.0, "daily_vol": 0.022, "drift": 0.0007},
    {"name": "JPM", "start_price": 155.0, "daily_vol": 0.013, "drift": 0.0004},
    {"name": "XOM", "start_price": 105.0, "daily_vol": 0.014, "drift": 0.0002},
    {"name": "KO", "start_price": 60.0, "daily_vol": 0.009, "drift": 0.0002},
]

stocks = {}
for i, s in enumerate(STOCKS_DEFS):
    prices = generate_price_path(
        s["start_price"], s["daily_vol"], s["drift"], seed=200 + i
    )
    stocks[s["name"]] = {
        "name": s["name"],
        "prices": timeserie_to_dict(prices),
    }

with open(OUTPUT_DIR / "stocks.json", "w") as f:
    json.dump(stocks, f, indent=2)


# ---------------------------------------------------------------------------
# FUTURES (10 instances) — underlying referenced by name (via "underlying_name"
# + "underlying_type" to know which file to look it up in)
# ---------------------------------------------------------------------------
last_commodity_prices = {
    name: commodities[name]["spot_prices"]["Price"][-1] for name in commodities
}
last_stock_prices = {name: stocks[name]["prices"]["Price"][-1] for name in stocks}

FUTURES_DEFS = [
    {
        "name": "CL_AUG26",
        "underlying_name": "Crude Oil",
        "underlying_type": "commodity",
        "maturity": "2026-08-15",
        "contract_size": 1000,
    },
    {
        "name": "BZ_SEP26",
        "underlying_name": "Brent Oil",
        "underlying_type": "commodity",
        "maturity": "2026-09-15",
        "contract_size": 1000,
    },
    {
        "name": "NG_JUL26",
        "underlying_name": "Natural Gas",
        "underlying_type": "commodity",
        "maturity": "2026-07-15",
        "contract_size": 10000,
    },
    {
        "name": "GC_OCT26",
        "underlying_name": "Gold",
        "underlying_type": "commodity",
        "maturity": "2026-10-15",
        "contract_size": 100,
    },
    {
        "name": "SI_DEC26",
        "underlying_name": "Silver",
        "underlying_type": "commodity",
        "maturity": "2026-12-15",
        "contract_size": 5000,
    },
    {
        "name": "HG_NOV26",
        "underlying_name": "Copper",
        "underlying_type": "commodity",
        "maturity": "2026-11-15",
        "contract_size": 25000,
    },
    {
        "name": "ZC_SEP26",
        "underlying_name": "Corn",
        "underlying_type": "commodity",
        "maturity": "2026-09-15",
        "contract_size": 5000,
    },
    {
        "name": "AAPL_SEP26",
        "underlying_name": "AAPL",
        "underlying_type": "stock",
        "maturity": "2026-09-18",
        "contract_size": 100,
    },
    {
        "name": "TSLA_DEC26",
        "underlying_name": "TSLA",
        "underlying_type": "stock",
        "maturity": "2026-12-18",
        "contract_size": 100,
    },
    {
        "name": "NVDA_JUN27",
        "underlying_name": "NVDA",
        "underlying_type": "stock",
        "maturity": "2027-06-18",
        "contract_size": 100,
    },
]

futures = {}
for f in FUTURES_DEFS:
    if f["underlying_type"] == "commodity":
        last_price = last_commodity_prices[f["underlying_name"]]
    else:
        last_price = last_stock_prices[f["underlying_name"]]

    # contract_price close to the last spot, with a small bounded contango/backwardation (+-3%)
    seed = abs(hash(f["name"])) % (2**32)
    rng = np.random.default_rng(seed)
    contract_price = round(last_price * (1 + rng.uniform(-0.03, 0.03)), 2)

    futures[f["name"]] = {
        "name": f["name"],
        "underlying_name": f["underlying_name"],
        "underlying_type": f["underlying_type"],
        "contract_price": contract_price,
        "maturity": f["maturity"],
        "contract_size": f["contract_size"],
    }

with open(OUTPUT_DIR / "futures.json", "w") as f:
    json.dump(futures, f, indent=2)

print(f"Database generated in {OUTPUT_DIR}/")
print(f"  - commodities.json : {len(commodities)} instances")
print(f"  - stocks.json       : {len(stocks)} instances")
print(f"  - futures.json      : {len(futures)} instances")
print(f"  - {N_DAYS} points per series, from {DATES[0].date()} to {DATES[-1].date()}")
