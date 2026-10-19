"""Display formatting shared by the single-PN report and the bulk output."""
from typing import Optional

from data.specs import SIZE_METRIC_TO_INCH
from utils.resistor_code import format_res

_STATUS_EN = {
    "厚膜/対象外": "Thick Film (Out of Scope)",
    "不明(コード未定義)": "Unknown (Undefined Code)",
    "不明(Panasonic形式不一致)": "Unknown (Panasonic Format Mismatch)",
    "不明(Panasonicコード未定義)": "Unknown (Panasonic Undefined Code)",
    "範囲外(Panasonic ERAレンジ未定義)": "Out of Range (Panasonic ERA Range Undefined)",
    "範囲外(Panasonic ERAレンジ外)": "Out of Range (Panasonic ERA Range)",
}


def fmt_size(size: Optional[str]) -> str:
    return size or "-"


def fmt_size_with_inch(size: Optional[str]) -> str:
    if not size:
        return "-"
    inch = SIZE_METRIC_TO_INCH.get(size)
    return f"{size}（{inch}）" if inch else size


def fmt_res(res: Optional[float]) -> str:
    return format_res(res) if res is not None else "-"


def fmt_tol(tol: Optional[float]) -> str:
    return f"±{tol:g}%" if tol is not None else "-"


def fmt_tcr(tcr: Optional[int]) -> str:
    return f"±{tcr} ppm/℃" if tcr is not None else "-"


def translate_status(status_jp: str) -> str:
    """English version of a parser status string."""
    if status_jp in _STATUS_EN:
        return _STATUS_EN[status_jp]
    if status_jp.startswith("不明("):
        return "Unknown (Undefined Code)"
    if "範囲外" in status_jp:
        return status_jp.replace("範囲外", "Out of Range")
    if "薄膜" in status_jp:
        return status_jp.replace("薄膜", "Thin Film")
    return status_jp
