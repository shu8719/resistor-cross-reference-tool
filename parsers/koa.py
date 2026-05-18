import re
from typing import Optional

from data.susumu_specs import KOA_RN73H_RANGE, KOA_RN73R_RANGE, KOA_TCR_ALLOWED, SIZE_MAP_KOA
from services.models import ParsedPN
from utils.resistor_code import parse_digit_code

RE_KOA_RN73 = re.compile(r"RN73([HR])(1E|1J|2A|2B|2E)[A-Z]*([0-9R]{4})([ABCDF])([0-9]{2,3})")


def parse_koa(pn: str) -> Optional[ParsedPN]:
    m = RE_KOA_RN73.search(pn)
    if not m:
        return None
    series_code = m.group(1)
    size = SIZE_MAP_KOA.get(m.group(2))
    res = parse_digit_code(m.group(3))
    tol_map = {"A": 0.05, "B": 0.1, "C": 0.25, "D": 0.5, "F": 1.0}
    tol_code = m.group(4)
    if tol_code not in tol_map:
        return None
    tol = tol_map[tol_code]

    tcr = int(m.group(5))
    if tcr not in KOA_TCR_ALLOWED:
        return None

    size_code = m.group(2)
    range_table = None
    if series_code == "R":
        range_table = KOA_RN73R_RANGE.get(size_code)
        if range_table is None:
            return ParsedPN(
                status_jp="範囲外(KOA RN73Rレンジ未定義)",
                size=size,
                res_ohm=res,
                tol_pct=tol,
                tcr_ppm=tcr,
            )
    elif series_code == "H":
        range_table = KOA_RN73H_RANGE.get(size_code)
        if range_table is None:
            return ParsedPN(
                status_jp="範囲外(KOA RN73Hレンジ未定義)",
                size=size,
                res_ohm=res,
                tol_pct=tol,
                tcr_ppm=tcr,
            )

    if range_table:
        if tcr not in range_table:
            return ParsedPN(
                status_jp=f"範囲外(KOA RN73{series_code}レンジ未定義)",
                size=size,
                res_ohm=res,
                tol_pct=tol,
                tcr_ppm=tcr,
            )
        min_r, max_r = range_table[tcr]
        if not (min_r <= res <= max_r):
            return ParsedPN(
                status_jp=f"範囲外(KOA RN73{series_code})",
                size=size,
                res_ohm=res,
                tol_pct=tol,
                tcr_ppm=tcr,
            )

    return ParsedPN(status_jp=f"薄膜(KOA RN73{series_code})", size=size, res_ohm=res, tol_pct=tol, tcr_ppm=tcr)

