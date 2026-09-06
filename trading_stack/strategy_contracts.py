from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


class StrategyContractError(ValueError):
    """Raised when a stored/editor strategy rule cannot be interpreted safely."""


_INDICATOR_ALIASES = {
    "bollinger bands": "bbands",
    "bollinger_bands": "bbands",
    "bb": "bbands",
}

_OPERATOR_ALIASES = {
    ">": "above",
    "above": "above",
    "<": "below",
    "below": "below",
    "==": "equals",
    "=": "equals",
    "equals": "equals",
    ">=": "above_or_equal",
    "above_or_equal": "above_or_equal",
    "<=": "below_or_equal",
    "below_or_equal": "below_or_equal",
    "crosses_above": "crosses_above",
    "crosses_below": "crosses_below",
    "increasing": "increasing",
    "decreasing": "decreasing",
}


def _indicator_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyContractError("indicator type must be a non-blank string")
    name = value.strip().lower()
    return _INDICATOR_ALIASES.get(name, name)


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StrategyContractError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise StrategyContractError(f"{field} must be finite")
    return number


def _normalize_params(name: str, raw: object) -> dict[str, Any]:
    if raw is None:
        params: dict[str, Any] = {}
    elif isinstance(raw, Mapping):
        params = dict(raw)
    else:
        raise StrategyContractError(f"parameters for {name} must be an object")

    if name == "bbands" and "std_dev" in params:
        std_dev = params.pop("std_dev")
        params.setdefault("dev_up", std_dev)
        params.setdefault("dev_down", std_dev)

    for key, value in tuple(params.items()):
        if key in {
            "period",
            "fast_period",
            "slow_period",
            "signal_period",
            "k_period",
            "d_period",
            "slowing",
            "conversion_period",
            "base_period",
            "lagging_span_period",
            "displacement",
        }:
            number = _finite_number(value, f"{name}.{key}")
            if number <= 0 or not number.is_integer():
                raise StrategyContractError(f"{name}.{key} must be a positive integer")
            params[key] = int(number)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            params[key] = _finite_number(value, f"{name}.{key}")
    return params


def indicator_column(name: str, params: Mapping[str, Any]) -> str:
    """Return the deterministic DataFrame column produced for an indicator."""
    name = _indicator_name(name)
    if name == "price":
        return "close"
    if name == "sma":
        return f"sma_{params.get('period', 20)}"
    if name == "ema":
        return f"ema_{params.get('period', 20)}"
    if name == "wma":
        return f"wma_{params.get('period', 20)}"
    if name == "rsi":
        return f"rsi_{params.get('period', 14)}"
    if name == "bbands":
        return "bb_middle"
    return {
        "macd": "macd",
        "stochastic": "stoch_k",
        "atr": "atr",
        "adx": "adx",
        "obv": "obv",
        "cci": "cci",
        "ichimoku": "ichimoku_conversion",
        "ichimoku cloud": "ichimoku_conversion",
        "engulfing": "bullish_engulfing",
    }.get(name, name)


def _indicator_entries(raw_config: object) -> list[tuple[str, dict[str, Any], object]]:
    if raw_config is None:
        return []
    if isinstance(raw_config, Mapping):
        entries = []
        for key, value in raw_config.items():
            if not isinstance(value, Mapping):
                raise StrategyContractError("indicator configuration values must be objects")
            value_dict = dict(value)
            name = _indicator_name(value_dict.pop("type", key))
            params = value_dict.pop("parameters", value_dict)
            entries.append((name, _normalize_params(name, params), key))
        return entries
    if isinstance(raw_config, Sequence) and not isinstance(raw_config, (str, bytes)):
        entries = []
        for item in raw_config:
            if not isinstance(item, Mapping):
                raise StrategyContractError("indicator array entries must be objects")
            name = _indicator_name(item.get("type"))
            params = _normalize_params(name, item.get("parameters", {}))
            entries.append((name, params, item.get("id")))
        return entries
    raise StrategyContractError("indicators_config must be an object or array")


def normalize_indicators_config(raw_config: object) -> dict[str, dict[str, Any]]:
    """Convert stored keyed or editor-array indicators to the calculation shape."""
    normalized: dict[str, dict[str, Any]] = {}
    for name, params, _ in _indicator_entries(raw_config):
        if name in normalized:
            raise StrategyContractError(f"duplicate indicator type is ambiguous: {name}")
        normalized[name] = params
    return normalized


def normalize_operator(operator: object) -> str:
    if not isinstance(operator, str):
        raise StrategyContractError("operator must be a string")
    try:
        return _OPERATOR_ALIASES[operator.strip().lower()]
    except KeyError as exc:
        raise StrategyContractError(f"unsupported operator: {operator}") from exc


def normalize_strategy_contract(
    raw_indicators: object, raw_conditions: object
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Normalize an editor/ORM strategy payload without guessing rule intent."""
    entries = _indicator_entries(raw_indicators)
    indicators = normalize_indicators_config(raw_indicators)
    references: dict[str, str] = {"price": "close", "close": "close"}
    for name, params, source_id in entries:
        column = indicator_column(name, params)
        references[name] = column
        references[column] = column
        if source_id is not None:
            references[f"{name}_{source_id}"] = column

    if raw_conditions is None:
        raw_conditions = []
    if not isinstance(raw_conditions, Sequence) or isinstance(raw_conditions, (str, bytes)):
        raise StrategyContractError("conditions must be an array")

    conditions: list[dict[str, Any]] = []
    for raw in raw_conditions:
        if not isinstance(raw, Mapping):
            raise StrategyContractError("condition entries must be objects")
        side_value = raw.get("side")
        signal_value = raw.get("signal_type")
        if side_value is None and signal_value is None:
            raise StrategyContractError("condition side is required")
        if side_value is not None and signal_value is not None:
            if str(side_value).upper() != str(signal_value).upper():
                raise StrategyContractError("condition side fields conflict")
        side = str(signal_value if signal_value is not None else side_value).upper()
        if side not in {"BUY", "SELL"}:
            raise StrategyContractError("condition side must be BUY or SELL")

        reference = raw.get("indicator")
        if not isinstance(reference, str) or reference not in references:
            raise StrategyContractError(f"unknown indicator reference: {reference}")
        conditions.append(
            {
                "indicator": references[reference],
                "operator": normalize_operator(raw.get("operator")),
                "value": _finite_number(raw.get("value"), "condition value"),
                "signal_type": side,
            }
        )
    return indicators, conditions
