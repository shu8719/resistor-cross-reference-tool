from typing import Dict, NamedTuple, Optional, Tuple

from data.packaging import RGV_PACKAGING_TABLE
from data.specs import (
    RG_SPECS,
    RG_TCR_ALLOWED,
    RG_TCR_CODE,
    RG_TOL_CODE,
    RGV_SPECS,
    RGV_TCR_ALLOWED,
    RGV_TOL_CODE,
)
from utils.resistor_code import get_rg_res_code, is_e24, is_e96

# Why a proposal could not be made (Proposal.reason)
REASON_SIZE = "size"            # size not covered by RG / RGV
REASON_TCR = "tcr"              # TCR not offered for this size
REASON_SERIES = "series"        # resistance is not an E24 / E96 value
REASON_TOL = "tol"              # no equal-or-tighter tolerance available
REASON_RANGE = "range"          # resistance outside the manufacturing range
REASON_PACKAGING = "packaging"  # packaging code table missing (RGV)


class Proposal(NamedTuple):
    grade: str            # "◎" when a part is proposed, otherwise "！"
    pn: str               # proposed part number ("" when none)
    note_jp: str
    note_en: str
    series: str           # "RG" or "RGV"
    reason: Optional[str] = None  # one of REASON_*, None when grade is "◎"


def _reject(reason: str, note_jp: str, note_en: str, series: str) -> Proposal:
    return Proposal("！", "", note_jp, note_en, series, reason)


def _select_tol_code(tol: float, codes: Dict[str, float]) -> Optional[str]:
    """Loosest catalog tolerance that is still equal to or tighter than `tol`.

    Never proposes a looser part. Requests tighter than the catalog minimum,
    or looser than ±0.5%, are rejected (None).
    """
    candidates = [(pct, code) for code, pct in codes.items() if pct <= tol + 1e-9]
    if not candidates or tol > 0.5:
        return None
    return max(candidates)[1]


def resolve_packaging(series: str, size: str, tol_code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if series == "RG":
        if size == "0603" or tol_code == "D":
            return "T10", None, None
        return "T5", None, None

    packaging = RGV_PACKAGING_TABLE.get((series, size, tol_code))
    if packaging is None:
        return None, "範囲外(RGV包装未定義)", "Out of Range (RGV Packaging Undefined)"
    return packaging, None, None


def generate_proposal(size: Optional[str], res: float, tol: float, tcr: int) -> Proposal:
    series = "RGV" if size == "3225" else "RG"

    if size is None:
        return _reject(REASON_SIZE, "範囲外(サイズ対象外)", "Out of Range (Size Not Supported)", series)

    if series == "RG" and tcr not in RG_TCR_ALLOWED:
        return _reject(REASON_TCR, "範囲外(RG TCRレンジ未定義)", "Out of Range (RG TCR Range Undefined)", series)
    if series == "RGV" and tcr not in RGV_TCR_ALLOWED:
        return _reject(REASON_TCR, "範囲外(RGV TCRレンジ未定義)", "Out of Range (RGV TCR Range Undefined)", series)

    if not (is_e24(res) or is_e96(res)):
        return _reject(REASON_SERIES, "範囲外(抵抗値系列対象外)", "Out of Range (Resistance Series Not Supported)", series)

    tol_code = _select_tol_code(tol, RG_TOL_CODE if series == "RG" else RGV_TOL_CODE)
    if tol_code is None:
        return _reject(REASON_TOL, "範囲外(公差対象外)", "Out of Range (Tolerance Not Supported)", series)

    spec = RG_SPECS.get(size) if series == "RG" else RGV_SPECS.get(size)
    if not spec:
        return _reject(REASON_SIZE, "範囲外(サイズ対象外)", "Out of Range (Size Not Supported)", series)

    note_jp, note_en = f"{series}シリーズ", f"{series} Series"
    if series == "RG":
        rg_by_tcr = spec.get(tcr)
        if rg_by_tcr is None:
            return _reject(REASON_TCR, "範囲外(RG TCRレンジ未定義)", "Out of Range (RG TCR Range Undefined)", series)
        rg_range = rg_by_tcr.get(tol_code)
        if rg_range is None:
            return _reject(REASON_RANGE, "範囲外(RGレンジ未定義)", "Out of Range (RG Range Undefined)", series)
        min_r, max_r = rg_range
    else:
        rgv_range = spec.get(tcr)
        if rgv_range is None:
            return _reject(REASON_TCR, "範囲外(RGV TCRレンジ未定義)", "Out of Range (RGV TCR Range Undefined)", series)
        min_r, max_r = rgv_range

    if not (min_r <= res <= max_r):
        # Recovery: if RG is out of range but RGV covers it (high resistance), switch to RGV
        rgv_range = RGV_SPECS.get(size, {}).get(tcr) if series == "RG" and tcr in RGV_TCR_ALLOWED else None
        if not (rgv_range and rgv_range[0] <= res <= rgv_range[1]):
            return _reject(REASON_RANGE, f"範囲外({series}レンジ外)", f"Out of Range ({series})", series)
        series = "RGV"
        note_jp, note_en = "RGV推奨(高抵抗)", "RGV Recommended (High Res)"
        tol_code = _select_tol_code(tol, RGV_TOL_CODE)
        if tol_code is None:
            return _reject(REASON_TOL, "範囲外(公差対象外)", "Out of Range (Tolerance Not Supported)", series)

    packaging, pkg_note_jp, pkg_note_en = resolve_packaging(series, size, tol_code)
    if packaging is None:
        return _reject(REASON_PACKAGING, pkg_note_jp, pkg_note_en, series)

    pn = f"{series}{size}{RG_TCR_CODE[tcr]}-{get_rg_res_code(res, size, series)}-{tol_code}-{packaging}"
    return Proposal("◎", pn, note_jp, note_en, series)
