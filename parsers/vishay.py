import re
from typing import Optional

from data.susumu_specs import SIZE_INCH_TO_METRIC
from services.models import ParsedPN
from utils.resistor_code import parse_rkm_string

RE_VISHAY_TNPW = re.compile(r"^TNPW(\d{4})([0-9RKM]+)([BDF])([HEXY])([A-Z0-9]{2})$")


def parse_vishay(pn: str) -> Optional[ParsedPN]:
    m = RE_VISHAY_TNPW.search(pn)
    if not m:
        return None
    size = SIZE_INCH_TO_METRIC.get(m.group(1))
    res = parse_rkm_string(m.group(2))
    tol = {"B": 0.1, "D": 0.5, "F": 1.0}.get(m.group(3))
    tcr = {"Y": 10, "X": 15, "E": 25, "H": 50}.get(m.group(4))
    if size is None or tol is None or tcr is None:
        return None
    return ParsedPN(status_jp="薄膜(Vishay TNPW)", size=size, res_ohm=res, tol_pct=tol, tcr_ppm=tcr)

