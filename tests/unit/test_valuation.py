import numpy as np
import pandas as pd
import pytest
from backend.finance.valuation import annualization_factor, convert_history_to_usd, position_value
from backend.finance.returns import calculate_log_returns
from backend.finance.metrics import calculate_expected_returns, calculate_covariance_matrix


def test_historical_fx_removes_peso_devaluation_not_asset_return():
    dates = pd.date_range("2024-01-01", periods=4)
    prices = pd.DataFrame({"ARS_ASSET": [1000, 1100, 1210, 1331], "USD_ASSET": [10, 11, 12, 13]}, index=dates)
    mep = pd.Series([100, 110, 121, 133.1], index=dates)
    converted = convert_history_to_usd(prices, {"ARS_ASSET": "ARS", "USD_ASSET": "USD"}, mep)
    np.testing.assert_allclose(converted["ARS_ASSET"], 10)
    np.testing.assert_allclose(converted["USD_ASSET"], prices["USD_ASSET"])


def test_missing_fx_does_not_use_future_or_current_rate():
    dates = pd.date_range("2024-01-01", periods=4)
    prices = pd.DataFrame({"ARS": [10, 11, 12, 13]}, index=dates)
    fx = pd.Series([2, 2, 2], index=dates[1:])
    result = convert_history_to_usd(prices, {"ARS": "ARS"}, fx)
    assert dates[0] not in result.index
    with pytest.raises(ValueError):
        convert_history_to_usd(prices, {"ARS": "ARS"})


def test_usd_cost_and_current_value_use_different_fx():
    assert position_value(10, 1000, "ARS", 100, "stock") == 100
    assert position_value(10, 1500, "ARS", 200, "stock") == 75
    assert position_value(100, 60, "USD", 1, "bond") == 60


def test_calendar_factors_and_analytical_annualization():
    assert annualization_factor(["BTC-USD", "ETH-USD"]) == 365
    assert annualization_factor(["AAPL", "MSFT"]) == 252
    assert annualization_factor(["BTC-USD", "AAPL"]) == 252
    returns = pd.DataFrame({"BTC-USD": [0.01, -0.01, 0.02]})
    assert calculate_expected_returns(returns, 365).iloc[0] == pytest.approx(365 * 0.02 / 3)
    assert calculate_covariance_matrix(returns, 365).iloc[0, 0] == pytest.approx(365 * np.var([0.01, -0.01, 0.02], ddof=1))


def test_mixed_calendar_keeps_weekend_crypto_movement():
    dates = pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09"])
    prices = pd.DataFrame({"BTC-USD": [100, 121, 110], "AAPL": [100, 102, 101]}, index=dates)
    assert calculate_log_returns(prices)["BTC-USD"].iloc[0] == pytest.approx(np.log(1.21))


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_bad_fx_rejected(value):
    with pytest.raises(ValueError):
        position_value(1, 100, "ARS", value, "stock")
