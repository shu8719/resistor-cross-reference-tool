import math
from typing import Optional, Set

from data.susumu_specs import E24_VALUES, E96_VALUES


def format_res(val: float) -> str:
    if val >= 1_000_000:
        return f"{val/1_000_000:g} MΩ"
    if val >= 1_000:
        return f"{val/1_000:g} kΩ"
    return f"{val:g} Ω"


def parse_rkm_string(res_str: str) -> float:
    """Parse competitor values like 10K, 4R7, 1M, etc."""
    res_str = res_str.upper()
    if "K" in res_str:
        return float(res_str.replace("K", ".")) * 1000
    if "M" in res_str:
        return float(res_str.replace("M", ".")) * 1_000_000
    if "R" in res_str:
        return float(res_str.replace("R", "."))
    return float(res_str)


def parse_digit_code(res_str: str) -> float:
    """Parse digit codes like 1002 (10.0k), 4R70, etc."""
    if "R" in res_str:
        return float(res_str.replace("R", "."))
    digits = float(res_str[:-1])
    multiplier = 10 ** int(res_str[-1])
    return digits * multiplier


def parse_yageo_rt_res_code(code: str) -> Optional[float]:
    code = code.upper()
    if "R" in code:
        return float(code.replace("R", "."))
    if "K" in code:
        return float(code.replace("K", ".")) * 1_000
    if "M" in code:
        return float(code.replace("M", ".")) * 1_000_000
    return None


def _series_mantissa(val: float) -> Optional[float]:
    if val <= 0:
        return None
    exponent = int(math.floor(math.log10(val)))
    return val / (10 ** exponent)


def _is_in_series(val: float, series_values: Set[float]) -> bool:
    mantissa = _series_mantissa(val)
    if mantissa is None:
        return False
    for nominal in series_values:
        if math.isclose(mantissa, nominal, rel_tol=1e-6, abs_tol=1e-6):
            return True
    return False


def is_e24(val: float) -> bool:
    """Strict E24 check."""
    return _is_in_series(val, E24_VALUES)


def is_e96(val: float) -> bool:
    """Strict E96 check."""
    return _is_in_series(val, E96_VALUES)


def get_susumu_res_code(val: float, size: str, series: str) -> str:
    """
    Generate Susumu nominal resistance code.
    Catalog rules:
      - RG: E24 -> 3 digit, E96 -> 4 digit, except RG3216 is always 4 digit.
      - RGV: always 4 digit.
    """
    use_4_digit = (series == "RGV") or (size == "3216")

    def code_3digit_with_r(v: float) -> Optional[str]:
        # Always 3 characters, using 'R' as decimal point.
        if v < 0:
            raise ValueError("resistance must be positive")
        if v < 1:
            # e.g. 0.10 -> R10, 0.47 -> R47
            n = int(round(v * 100))
            return f"R{n:02d}"
        if v < 10:
            i = int(v)
            d = int(round((v - i) * 10))
            # carry
            if d == 10:
                i += 1
                d = 0
            if i >= 10:
                return None
            return f"{i}R{d}"
        return None

    def code_4digit_with_r(v: float) -> Optional[str]:
        # Always 4 characters, using 'R' as decimal point.
        if v < 0:
            raise ValueError("resistance must be positive")
        if v < 1:
            # e.g. 0.100 -> R100, 0.470 -> R470
            n = int(round(v * 1000))
            return f"R{n:03d}"
        if v < 10:
            i = int(v)
            d2 = int(round((v - i) * 100))
            if d2 == 100:
                i += 1
                d2 = 0
            if i >= 10:
                return None
            return f"{i}R{d2:02d}"
        if v < 100:
            i = int(v)
            d1 = int(round((v - i) * 10))
            if d1 == 10:
                i += 1
                d1 = 0
            if i >= 100:
                return None
            return f"{i:02d}R{d1}"
        return None

    # RG E24 path (3-digit) unless forced 4-digit
    if (not use_4_digit) and is_e24(val):
        rcode = code_3digit_with_r(val)
        if rcode is not None:
            return rcode
        exp = int(math.floor(math.log10(val)))
        mantissa = val / (10**exp)
        mant_2 = int(round(mantissa * 10))
        zeros = exp - 1
        return f"{mant_2}{zeros}"

    # 4-digit path (RGV, RG3216, or non-E24)
    rcode4 = code_4digit_with_r(val)
    if rcode4 is not None:
        return rcode4
    exp = int(math.floor(math.log10(val)))
    mantissa = val / (10**exp)
    mant_3 = int(round(mantissa * 100))
    zeros = exp - 2
    return f"{mant_3}{zeros}"


def get_4digit_code(val: float) -> str:
    if val <= 0:
        raise ValueError("resistance must be positive")
    if val < 1:
        n = int(round(val * 1000))
        return f"R{n:03d}"
    if val < 10:
        i = int(val)
        d2 = int(round((val - i) * 100))
        if d2 == 100:
            i += 1
            d2 = 0
        if i >= 10:
            raise ValueError("resistance out of 4-digit range")
        return f"{i}R{d2:02d}"
    if val < 100:
        i = int(val)
        d1 = int(round((val - i) * 10))
        if d1 == 10:
            i += 1
            d1 = 0
        if i >= 100:
            raise ValueError("resistance out of 4-digit range")
        return f"{i:02d}R{d1}"
    exp = int(math.floor(math.log10(val)))
    mantissa = val / (10**exp)
    mant_3 = int(round(mantissa * 100))
    zeros = exp - 2
    if mant_3 >= 1000:
        mant_3 = 100
        zeros += 1
    return f"{mant_3}{zeros}"


def get_yageo_res_code(val: float) -> str:
    if val >= 1_000_000:
        return f"{val/1_000_000:g}M"
    if val >= 1_000:
        return f"{val/1_000:g}K"
    return f"{val:g}R"

