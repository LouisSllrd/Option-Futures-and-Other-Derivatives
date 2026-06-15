from chapters.chap3.futures import Asset
from chapters.chap3.positions import LinearExposition


def short_hedge():
    company_expo = LinearExposition(asset=Asset("rice"), sensitivity_factor=10 ^ 6)
