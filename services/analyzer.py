from data.susumu_specs import MELF_PREFIXES, OUT_OF_SCOPE_PREFIXES
from parsers.koa import parse_koa
from parsers.panasonic import parse_panasonic
from parsers.susumu import parse_susumu
from parsers.vishay import parse_vishay
from parsers.yageo import parse_yageo
from services.models import ParsedPN
from utils.normalize import normalize_pn


def translate_status(status_jp: str) -> str:
    map_en = {
        "Susumu純正": "Susumu Original",
        "厚膜/対象外": "Thick Film (Out of Scope)",
        "不明(コード未定義)": "Unknown (Undefined Code)",
        "不明(Panasonic形式不一致)": "Unknown (Panasonic Format Mismatch)",
        "不明(Panasonicコード未定義)": "Unknown (Panasonic Undefined Code)",
        "範囲外(Panasonic ERAレンジ未定義)": "Out of Range (Panasonic ERA Range Undefined)",
        "範囲外(Panasonic ERAレンジ外)": "Out of Range (Panasonic ERA Range)",
    }
    if status_jp in map_en:
        return map_en[status_jp]
    if status_jp.startswith("不明("):
        return "Unknown (Undefined Code)"
    if "範囲外" in status_jp:
        return status_jp.replace("範囲外", "Out of Range")
    if "薄膜" in status_jp:
        return status_jp.replace("薄膜", "Thin Film")
    return status_jp


def _parse_out_of_scope(pn: str):
    if pn.startswith(OUT_OF_SCOPE_PREFIXES):
        return ParsedPN(status_jp="厚膜/対象外")
    if pn.startswith(MELF_PREFIXES):
        return ParsedPN(status_jp="厚膜/対象外")
    return None


def parse_pn(pn: str) -> ParsedPN:
    raw = str(pn).strip()
    normalized = normalize_pn(raw)

    # Reverse mode first
    sus = parse_susumu(normalized)
    if sus:
        return sus

    # Strict filtering
    oos = _parse_out_of_scope(normalized)
    if oos:
        return oos

    # Competitors
    for parser in (parse_koa, parse_yageo, parse_vishay, parse_panasonic):
        parsed = parser(normalized)
        if parsed:
            return parsed

    return ParsedPN(status_jp="不明(コード未定義)")

