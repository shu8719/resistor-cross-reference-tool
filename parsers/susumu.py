import re
from typing import Optional

from data.susumu_specs import RG_SIZES, RGV_SIZES, SUSUMU_TCR_ALLOWED_RGV, SUSUMU_TOL_CODE_RG, SUSUMU_TOL_CODE_RGV
from services.models import ParsedPN
from utils.resistor_code import is_e24, is_e96

RE_SUSUMU = re.compile(r"^(RG|RGV)(\d{4})([NPQRV])([0-9R]{3,4})([BDFPW])")


def parse_susumu(pn: str) -> Optional[ParsedPN]:
    m = RE_SUSUMU.search(pn)
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
    if series == "RGV" and tcr not in SUSUMU_TCR_ALLOWED_RGV:
        return None

    tol_map = SUSUMU_TOL_CODE_RG if series == "RG" else SUSUMU_TOL_CODE_RGV
    if tol_code not in tol_map:
        return None
    tol = tol_map[tol_code]

    if "R" in res_str:
        res = float(res_str.replace("R", "."))
    else:
        digits = int(res_str[:-1])
        multiplier = 10 ** int(res_str[-1])
        res = digits * multiplier

    # Validate resistance series by rule
    if series == "RG" and size != "3216":
        if res_len == 3 and not is_e24(res):
            return None
        if res_len == 4 and not is_e96(res):
            return None
    else:
        if not (is_e24(res) or is_e96(res)):
            return None

    return ParsedPN(status_jp="Susumu純正", size=size, res_ohm=res, tol_pct=tol, tcr_ppm=tcr)

