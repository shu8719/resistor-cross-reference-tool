import re
from typing import Optional

from data.susumu_specs import SIZE_INCH_TO_METRIC, YAGEO_RT_RANGE_BY_SIZE, YAGEO_RT_TCR_CODE, YAGEO_RT_TOL_CODE
from services.models import ParsedPN
from utils.resistor_code import parse_yageo_rt_res_code

RE_YAGEO_RT = re.compile(
    r"^RT(0100|0201|0402|0603|0805|1206|1210|2010|2512)([LPWBCDF])([RK])([ABCDE])(07|10|13|7W)([0-9RKM]{2,4})L?$"
)


def parse_yageo(pn: str) -> Optional[ParsedPN]:
    if not pn.startswith("RT"):
        return None

    m = RE_YAGEO_RT.search(pn)
    if not m:
        return ParsedPN(status_jp="不明(コード未定義)")

    size_inch = m.group(1)
    tol = YAGEO_RT_TOL_CODE.get(m.group(2))
    tcr = YAGEO_RT_TCR_CODE.get(m.group(4))
    res = parse_yageo_rt_res_code(m.group(6))
    if tol is None or tcr is None or res is None:
        return ParsedPN(status_jp="不明(コード未定義)")

    range_spec = YAGEO_RT_RANGE_BY_SIZE.get(size_inch)
    if range_spec is None:
        return ParsedPN(status_jp="範囲外(YAGEO RTレンジ未定義)", tol_pct=tol, tcr_ppm=tcr, res_ohm=res)

    min_r, max_r = range_spec
    if not (min_r <= res <= max_r):
        return ParsedPN(status_jp="範囲外(YAGEO RTレンジ外)", tol_pct=tol, tcr_ppm=tcr, res_ohm=res)

    size = SIZE_INCH_TO_METRIC.get(size_inch)
    if size is None:
        return ParsedPN(status_jp="範囲外(YAGEO RTサイズ対象外)", tol_pct=tol, tcr_ppm=tcr, res_ohm=res)

    return ParsedPN(status_jp="薄膜(YAGEO RT)", size=size, res_ohm=res, tol_pct=tol, tcr_ppm=tcr)

