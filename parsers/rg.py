import re
from typing import Optional

from data.specs import RG_SIZES, RGV_SIZES, RGV_TCR_ALLOWED, RG_TOL_CODE, RGV_TOL_CODE
from parsers.models import STATUS_RG_SERIES, ParsedPN
from utils.resistor_code import is_e24, is_e96, parse_digit_code

RE_RG = re.compile(r"^(RG|RGV)(\d{4})([NPQRV])([0-9R]{3,4})([BDFPW])")


def _segments(pn: str, m: "re.Match[str]"):
    segs = [
        (m.group(1), "series"),
        (m.group(2), "size"),
        (m.group(3), "tcr"),
        (m.group(4), "res"),
        (m.group(5), "tol"),
    ]
    if m.end() < len(pn):
        segs.append((pn[m.end() :], "packaging"))
    return tuple(segs)


def parse_rg(pn: str) -> Optional[ParsedPN]:
    m = RE_RG.search(pn)
    if not m:
        return None
    series, size, tcr_code, res_str, tol_code = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    res_len = len(res_str)

    # Validate series/size rules
    if series == "RGV" and res_len != 4:
        return None
    if series == "RG" and size == "3225":
        return None
    if series == "RG" and size == "3216" and res_len != 4:
        return None
    if series == "RG" and size not in RG_SIZES:
        return None
    if series == "RGV" and size not in RGV_SIZES:
        return None

    tcr_map = {"V": 5, "N": 10, "P": 25, "Q": 50, "R": 100}
    if tcr_code not in tcr_map:
        return None
    tcr = tcr_map[tcr_code]
    if series == "RGV" and tcr not in RGV_TCR_ALLOWED:
        return None

    tol_map = RG_TOL_CODE if series == "RG" else RGV_TOL_CODE
    if tol_code not in tol_map:
        return None
    tol = tol_map[tol_code]

    res = parse_digit_code(res_str)
    if res is None:
        return None

    # Validate resistance series by rule
    if series == "RG" and size != "3216":
        if res_len == 3 and not is_e24(res):
            return None
        if res_len == 4 and not is_e96(res):
            return None
    else:
        if not (is_e24(res) or is_e96(res)):
            return None

    return ParsedPN(
        status_jp=STATUS_RG_SERIES,
        size=size,
        res_ohm=res,
        tol_pct=tol,
        tcr_ppm=tcr,
        series=series,
        segments=_segments(pn, m),
        tol_span=m.span(5),
    )
