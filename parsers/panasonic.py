import re
from typing import Optional

from data.susumu_specs import (
    PANA_ERA_A_TO_INCH,
    PANA_ERA_PKG_CODE,
    PANA_ERA_RANGE,
    PANA_ERA_TCR_CODE,
    PANA_ERA_TOL_CODE,
    SIZE_INCH_TO_METRIC,
)
from services.models import ParsedPN
from utils.resistor_code import parse_digit_code

RE_PANA_ERA_A = re.compile(r"^ERA(?:\-)?(?P<st>(1A|2A|3A|6A|8A))(?P<tcr>[RPEHK])(?P<tol>[WBCD])(?P<res>\d{3,4})(?P<pkg>[CXV])$")
RE_PANA_ERA_LOOSE = re.compile(r"^ERA(?:\-)?(?P<st>[0-9A-Z]{2})(?P<tcr>[A-Z])(?P<tol>[A-Z])(?P<res>[0-9A-Z]{3,4})(?P<pkg>[A-Z])$")


def _segments(m: "re.Match[str]"):
    return (
        ("ERA", "series"),
        (m.group("st"), "size"),
        (m.group("tcr"), "tcr"),
        (m.group("tol"), "tol"),
        (m.group("res"), "res"),
        (m.group("pkg"), "packaging"),
    )


def parse_panasonic(pn: str) -> Optional[ParsedPN]:
    if not pn.startswith("ERA"):
        return None

    loose = RE_PANA_ERA_LOOSE.search(pn)
    if not loose:
        return ParsedPN(status_jp="不明(Panasonic形式不一致)", maker="Panasonic", series="ERA")

    strict = RE_PANA_ERA_A.search(pn)
    if not strict:
        return ParsedPN(status_jp="不明(Panasonicコード未定義)", maker="Panasonic", series="ERA", segments=_segments(loose))

    st = strict.group("st")
    tcr_code = strict.group("tcr")
    tol_code = strict.group("tol")
    res_code = strict.group("res")
    pkg_code = strict.group("pkg")
    common = dict(maker="Panasonic", series=f"ERA{st}", segments=_segments(strict), tol_span=strict.span("tol"))

    size_inch = PANA_ERA_A_TO_INCH.get(st)
    size = SIZE_INCH_TO_METRIC.get(size_inch) if size_inch else None
    tcr = PANA_ERA_TCR_CODE.get(tcr_code)
    tol = PANA_ERA_TOL_CODE.get(tol_code)
    pkg = PANA_ERA_PKG_CODE.get(pkg_code)
    if size is None or tcr is None or tol is None or pkg is None:
        return ParsedPN(status_jp="不明(Panasonicコード未定義)", **common)

    res = parse_digit_code(res_code)
    if res is None:
        return ParsedPN(status_jp="不明(Panasonicコード未定義)", **common)
    specs = dict(size=size, res_ohm=res, tol_pct=tol, tcr_ppm=tcr, **common)
    range_table = PANA_ERA_RANGE.get(st)
    if range_table is None:
        return ParsedPN(status_jp="範囲外(Panasonic ERAレンジ未定義)", **specs)

    range_spec = range_table.get((tcr, tol))
    if range_spec is None:
        return ParsedPN(status_jp="範囲外(Panasonic ERAレンジ未定義)", **specs)

    min_r, max_r = range_spec
    if not (min_r <= res <= max_r):
        return ParsedPN(status_jp="範囲外(Panasonic ERAレンジ外)", **specs)

    return ParsedPN(status_jp=f"薄膜(Panasonic ERA-{st})", pkg_code=pkg_code, **specs)
