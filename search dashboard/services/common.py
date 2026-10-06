import math


def _nan_to_none(value):
    """Pandas yields NaN for missing values; NaN is not valid JSON."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        import pandas as pd
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):  # numpy scalar -> python
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def build_row(symbol=None, full_name=None, underlying=None, exchange=None, segment=None,
              expiry=None, strike=None, option_type=None, token=None):
    return {
        "symbol": _nan_to_none(symbol),
        "full_name": _nan_to_none(full_name),
        "underlying": _nan_to_none(underlying),
        "exchange": _nan_to_none(exchange),
        "segment": _nan_to_none(segment),
        "expiry": _nan_to_none(expiry),
        "strike": _nan_to_none(strike),
        "option_type": _nan_to_none(option_type),
        "price": None,
        "change_pct": None,
        "_token": _nan_to_none(token),
        "_volume": None,
    }


def option_type_from_symbol(symbol):
    s = (_nan_to_none(symbol) or "").upper()
    if s.endswith("CE"):
        return "CE"
    if s.endswith("PE"):
        return "PE"
    if s.endswith("FUT"):
        return "FUT"
    return None


def sort_by_liquidity(rows):
    """Sort by _volume desc, only if any row has volume data."""
    if not any(r.get("_volume") for r in rows):
        return rows
    return sorted(rows, key=lambda r: r.get("_volume") or 0, reverse=True)


def compute_change_pct(last, prev_close):
    try:
        if last is None or not prev_close:
            return None
        return round((float(last) - float(prev_close)) / float(prev_close) * 100, 2)
    except (TypeError, ValueError):
        return None


def strip_internal_fields(row):
    return {k: v for k, v in row.items() if not k.startswith("_")}
