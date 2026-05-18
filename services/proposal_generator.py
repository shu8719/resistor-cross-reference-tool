from typing import Optional, Tuple

from data.packaging import RGV_PACKAGING_TABLE
from data.susumu_specs import (
    SUSUMU_SPECS_RG,
    SUSUMU_SPECS_RGV,
    SUSUMU_TCR_ALLOWED_RG,
    SUSUMU_TCR_ALLOWED_RGV,
    SUSUMU_TCR_CODE,
)
from utils.resistor_code import get_susumu_res_code, is_e24, is_e96


def resolve_packaging(series: str, size: str, tol_code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if series == "RG":
        if size == "0603":
            return "T10", None, None
        if tol_code == "D":
            return "T10", None, None
        return "T5", None, None

    packaging = RGV_PACKAGING_TABLE.get((series, size, tol_code))
    if packaging is None:
        return None, "範囲外(RGV包装未定義)", "Out of Range (RGV Packaging Undefined)"
    return packaging, None, None


def generate_proposal(size: Optional[str], res: float, tol: float, tcr: int) -> Tuple[str, str, str, str, str]:
    series = "RGV" if size == "3225" else "RG"

    if size is None:
        return "！", "", "範囲外(サイズ対象外)", "Out of Range (Size Not Supported)", series

    if series == "RG" and tcr not in SUSUMU_TCR_ALLOWED_RG:
        return "！", "", "範囲外(RG TCRレンジ未定義)", "Out of Range (RG TCR Range Undefined)", series
    if series == "RGV" and tcr not in SUSUMU_TCR_ALLOWED_RGV:
        return "！", "", "範囲外(RGV TCRレンジ未定義)", "Out of Range (RGV TCR Range Undefined)", series

    res_series_ok = is_e24(res) or is_e96(res)
    if not res_series_ok:
        return "！", "", "範囲外(抵抗値系列対象外)", "Out of Range (Resistance Series Not Supported)", series

    def select_tol_code_rg(v: float) -> Optional[str]:
        if v <= 0.02:
            return "P"
        if v <= 0.05:
            return "W"
        if v <= 0.1:
            return "B"
        if v <= 0.5:
            return "D"
        return None

    def select_tol_code_rgv(v: float) -> Optional[str]:
        if v <= 0.1:
            return "B"
        if v <= 0.5:
            return "D"
        return None

    s_tol = select_tol_code_rg(tol) if series == "RG" else select_tol_code_rgv(tol)
    if s_tol is None:
        return "！", "", "範囲外(公差対象外)", "Out of Range (Tolerance Not Supported)", series

    spec = SUSUMU_SPECS_RG.get(size) if series == "RG" else SUSUMU_SPECS_RGV.get(size)
    note_jp, note_en = f"{series}シリーズ", f"{series} Series"

    if spec:
        if series == "RG":
            rg_by_tcr = spec.get(tcr)
            if rg_by_tcr is None:
                return "！", "", "範囲外(RG TCRレンジ未定義)", "Out of Range (RG TCR Range Undefined)", series

            rg_spec = rg_by_tcr.get(s_tol)
            if rg_spec is None:
                return "！", "", "範囲外(RGレンジ未定義)", "Out of Range (RG Range Undefined)", series

            min_r, max_r = rg_spec
        else:
            rgv_spec = spec.get(tcr)
            if rgv_spec is None:
                return "！", "", "範囲外(RGV TCRレンジ未定義)", "Out of Range (RGV TCR Range Undefined)", series
            min_r, max_r = rgv_spec

        if not (min_r <= res <= max_r):
            # Recovery: if RG is out-of-range but RGV can produce, switch to RGV
            if series == "RG" and size in SUSUMU_SPECS_RGV and tcr in SUSUMU_TCR_ALLOWED_RGV:
                rgv_spec = SUSUMU_SPECS_RGV[size].get(tcr)
                if rgv_spec and (rgv_spec[0] <= res <= rgv_spec[1]):
                    series = "RGV"
                    note_jp, note_en = "RGV推奨(高抵抗)", "RGV Recommended (High Res)"
                    s_tol = select_tol_code_rgv(tol)
                    if s_tol is None:
                        return "！", "", "範囲外(公差対象外)", "Out of Range (Tolerance Not Supported)", series
                else:
                    return "！", "", "範囲外(RGレンジ外)", "Out of Range (RG)", series
            else:
                return "！", "", f"範囲外({series}レンジ外)", f"Out of Range ({series})", series
    else:
        return "！", "", "範囲外(サイズ対象外)", "Out of Range (Size Not Supported)", series

    s_tcr = SUSUMU_TCR_CODE[tcr]
    s_res = get_susumu_res_code(res, size, series)
    packaging, pkg_note_jp, pkg_note_en = resolve_packaging(series, size, s_tol)
    if packaging is None:
        return "！", "", pkg_note_jp or "範囲外(包装未定義)", pkg_note_en or "Out of Range (Packaging Undefined)", series

    proposal = f"{series}{size}{s_tcr}-{s_res}-{s_tol}-{packaging}"
    return "◎", proposal, note_jp, note_en, series

