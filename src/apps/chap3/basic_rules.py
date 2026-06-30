"""
Demonstrates the hedging API on top of the local Database, mirroring
Hull's chapter 3 examples (basic hedge, basis risk, cross hedging, and
stock index futures / beta hedging).

Each case is reported in three stages:
  1. INITIAL SITUATION  - the unhedged exposure, in plain terms.
  2. INTERMEDIATE STEPS - the inputs and formula used to size the hedge.
  3. SOLUTION / FINAL STATE - the hedging position(s) taken and the
     resulting residual exposure (ideally ~0 for a full hedge).
"""

import pandas as pd

from core.assets.derivatives.basis import CrossHedge
from core.assets.derivatives.futures import StockIndexFuture
from core.hedging_strategies import BetaHedging, CrossHedgeStrategy, FutureHedging
from core.portfolios import Portfolio
from core.positions import SpotPosition
from db.connection import DatabaseConnection

TODAY = pd.Timestamp("2026-06-21")

SECTION_WIDTH = 78


def _header(title: str) -> None:
    print("\n" + "=" * SECTION_WIDTH)
    print(title)
    print("=" * SECTION_WIDTH)


def _subheader(title: str) -> None:
    print(f"\n[{title}]")


def simple_future_hedge() -> None:
    """A producer holding crude oil hedges it with the nearest matching future."""
    _header("CASE 1 — Simple future hedge (Hull 3.1/3.2): long crude oil spot")

    db = DatabaseConnection()
    crude_oil = db.get_commodity("Crude Oil")

    quantity_held = 20_000  # barrels
    portfolio = Portfolio(
        positions=[
            SpotPosition(
                risk_free_rate=0.04,
                date=TODAY,
                quantity=quantity_held,
                asset=crude_oil,
                is_long=True,
            )
        ]
    )

    # -- 1. Initial situation -------------------------------------------
    _subheader("Initial situation")
    initial_exposure = portfolio.net_exposition_to(crude_oil)
    print("  Asset held        : Crude Oil (spot)")
    print(f"  Quantity held      : {quantity_held:,} barrels (long)")
    print("  Hedging in place   : none")
    print(f"  Net exposure       : {initial_exposure:,.2f} barrels of Crude Oil")

    # -- 2. Intermediate steps -------------------------------------------
    _subheader("Intermediate steps")
    strategy = FutureHedging(database=db, as_of=TODAY)
    future = db.find_future_for_underlying(crude_oil, as_of=TODAY)
    contracts_needed = round(abs(initial_exposure) / future.contract_size)
    print(f"  Future selected    : {future.name} (maturity {future.maturity.date()})")
    print(f"  Contract size      : {future.contract_size:,} barrels/contract")
    print("  Direction needed   : SHORT (offsetting a long spot exposure)")
    print(
        f"  Contracts needed   : |{initial_exposure:,.0f}| / {future.contract_size:,} "
        f"= {contracts_needed} contracts"
    )

    # -- 3. Solution / final state ---------------------------------------
    _subheader("Solution / final state")
    portfolio.hedge(strategy)
    for hedge in portfolio.hedging_positions:
        side = "long" if hedge.is_long else "short"
        print(
            f"  Hedge taken        : {side} {hedge.quantity} contracts of {hedge.future.name}"
        )

    final_exposure = portfolio.net_exposition_to(crude_oil)
    print(f"  Residual exposure  : {final_exposure:,.2f} barrels of Crude Oil")

    # Calling .hedge() again should not add anything: the residual
    # exposure is already 0 once the hedging position is accounted for.
    contracts_before = len(portfolio.hedging_positions)
    portfolio.hedge(FutureHedging(database=db, as_of=TODAY))
    assert len(portfolio.hedging_positions) == contracts_before, (
        "Re-hedging should be a no-op."
    )
    print(
        f"  Idempotence check  : re-calling .hedge() added "
        f"{len(portfolio.hedging_positions) - contracts_before} new positions (expected 0)"
    )


def cross_hedge_jet_fuel() -> None:
    """
    Hull Example 3.3: an airline hedges jet fuel exposure with heating-oil
    futures, since jet fuel futures aren't directly available. We reuse
    "Crude Oil" as the available proxy future for illustration purposes.
    """
    _header("CASE 2 — Cross hedge (Hull 3.4): jet fuel exposure, no direct future")

    db = DatabaseConnection()
    jet_fuel_proxy_asset = db.get_commodity(
        "Crude Oil"
    )  # stand-in underlying for the demo
    heating_oil_future = db.get_future("CL_AUG26")

    quantity_exposed = 2_000_000  # gallons of jet fuel exposure
    portfolio = Portfolio(
        positions=[
            SpotPosition(
                risk_free_rate=0.04,
                date=TODAY,
                quantity=quantity_exposed,
                asset=jet_fuel_proxy_asset,
                is_long=True,
            )
        ]
    )

    # -- 1. Initial situation -------------------------------------------
    _subheader("Initial situation")
    initial_exposure = portfolio.net_exposition_to(jet_fuel_proxy_asset)
    print("  Asset exposed      : Jet fuel (proxied here by Crude Oil)")
    print(f"  Quantity exposed   : {quantity_exposed:,} gallons (long)")
    print("  Direct future      : none available -> cross hedge required")
    print(f"  Net exposure       : {initial_exposure:,.2f} units")

    # -- 2. Intermediate steps -------------------------------------------
    _subheader("Intermediate steps")
    cross_hedge = CrossHedge(
        future=heating_oil_future,
        hedged_asset_prices=jet_fuel_proxy_asset.spot_prices,
    )
    h_star = cross_hedge.hedge_ratio()
    effectiveness = cross_hedge.hedge_effectiveness()
    contracts_needed = cross_hedge.optimal_contracts(abs(initial_exposure))
    print(
        f"  Proxy future       : {heating_oil_future.name} "
        f"(underlying: {heating_oil_future.underlying.name})"
    )
    print(
        f"  Minimum-variance hedge ratio h* = rho * (sigma_S / sigma_F) = {h_star:.4f}"
    )
    print(f"  Hedge effectiveness (R^2 = rho^2)               = {effectiveness:.4f}")
    print(f"  Contract size      : {heating_oil_future.contract_size:,} units/contract")
    print(
        f"  Contracts needed   : N* = h* * QA / QF "
        f"= {h_star:.4f} * {quantity_exposed:,} / {heating_oil_future.contract_size:,} "
        f"= {contracts_needed} contracts"
    )

    # -- 3. Solution / final state ---------------------------------------
    _subheader("Solution / final state")
    strategy = CrossHedgeStrategy(
        future_by_asset={jet_fuel_proxy_asset: heating_oil_future}
    )
    portfolio.hedge(strategy)
    for hedge in portfolio.hedging_positions:
        side = "long" if hedge.is_long else "short"
        print(
            f"  Hedge taken        : {side} {hedge.quantity} contracts of {hedge.future.name}"
        )

    final_exposure = portfolio.net_exposition_to(jet_fuel_proxy_asset)
    print(f"  Residual exposure  : {final_exposure:,.2f} units")
    if abs(h_star - 1.0) > 1e-6:
        print(
            "  Note               : residual is not exactly 0 because the hedge ratio"
        )
        print(
            f"                       (h* = {h_star:.4f}) departs from 1.0 — this is the"
        )
        print(
            "                       basis risk inherent to cross hedging with a proxy asset."
        )
    else:
        print(
            "  Note               : h* came out to 1.0 in this demo because the proxy"
        )
        print(
            "                       asset (Crude Oil) was reused as the 'jet fuel' stand-in."
        )
        print(
            "                       With a genuinely different proxy, expect h* != 1.0 and"
        )
        print("                       a small residual basis risk even after hedging.")


def beta_hedge_equity_portfolio() -> None:
    """
    Hull section 3.5: hedge a beta-1.5 equity portfolio down to beta 0
    using S&P-500-style mini index futures.
    """
    _header("CASE 3 — Beta hedge (Hull 3.5): equity portfolio vs. stock index future")

    db = DatabaseConnection()
    index_underlying = db.get_stock("AAPL")  # stand-in index proxy for the demo

    index_future = StockIndexFuture(
        name="SP500_MINI_SEP26",
        underlying=index_underlying,
        contract_price=1010.0,
        maturity=pd.Timestamp("2026-09-18"),
        contract_size=250,
        dividend_yield=0.01,
    )

    portfolio_value = 5_050_000
    beta = 1.5
    target_beta = 0.0
    portfolio = (
        Portfolio()
    )  # portfolio.value would normally drive sizing in a live setup

    # -- 1. Initial situation -------------------------------------------
    _subheader("Initial situation")
    print(f"  Portfolio value VA : ${portfolio_value:,.0f}")
    print(f"  Portfolio beta     : {beta}")
    print(f"  Target beta        : {target_beta}")
    print(f"  Market exposure    : the portfolio moves {beta}x the index on average")

    # -- 2. Intermediate steps -------------------------------------------
    _subheader("Intermediate steps")
    contract_value = index_future.contract_value
    beta_gap = beta - target_beta
    contracts_needed = round(abs(beta_gap) * portfolio_value / contract_value)
    print(
        f"  Index future       : {index_future.name} "
        f"(price {index_future.contract_price}, size {index_future.contract_size})"
    )
    print(
        f"  Contract value VF  : {index_future.contract_price} * "
        f"{index_future.contract_size} = ${contract_value:,.0f}"
    )
    print(f"  Beta gap to close  : {beta} - {target_beta} = {beta_gap}")
    print(
        f"  Contracts needed   : N* = beta_gap * VA / VF "
        f"= {beta_gap} * {portfolio_value:,} / {contract_value:,.0f} "
        f"= {contracts_needed} contracts"
    )

    # -- 3. Solution / final state ---------------------------------------
    _subheader("Solution / final state")
    strategy = BetaHedging(
        index_future=index_future, beta=beta, target_beta=target_beta
    )
    hedge = strategy.hedge_portfolio_value(portfolio_value=portfolio_value)
    portfolio.hedging_positions.append(hedge)

    side = "long" if hedge.is_long else "short"
    print(
        f"  Hedge taken        : {side} {hedge.quantity} contracts of {hedge.future.name}"
    )

    # The rounded contract count means the resulting beta is only
    # approximately the target; report the beta actually achieved.
    # Shorting `contracts` index futures reduces beta by
    # (contracts * VF / VA); going long would increase it by the same amount.
    beta_reduction = hedge.quantity * contract_value / portfolio_value
    achieved_beta = (
        beta - beta_reduction if not hedge.is_long else beta + beta_reduction
    )
    print(
        f"  Beta achieved      : ~{achieved_beta:.3f} "
        f"(target was {target_beta}; small gap is due to integer contract rounding)"
    )


if __name__ == "__main__":
    simple_future_hedge()
    cross_hedge_jet_fuel()
    beta_hedge_equity_portfolio()
    print()
