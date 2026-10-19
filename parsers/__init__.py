"""Part-number parsers: one module per maker, plus the dispatcher `parse_pn`."""
from data.specs import MELF_PREFIXES, OUT_OF_SCOPE_PREFIXES
from parsers.koa import parse_koa
from parsers.models import ParsedPN
from parsers.panasonic import parse_panasonic
from parsers.rg import parse_rg
from parsers.vishay import parse_vishay
from parsers.yageo import parse_yageo
from utils.normalize import normalize_pn

__all__ = ["ParsedPN", "parse_pn"]

# Maker names for the thick-film / MELF prefixes we reject (display only)
_OUT_OF_SCOPE_MAKER = {
    "UR73": "KOA", "WK73": "KOA", "SR73": "KOA", "RK73": "KOA",
    "RC": "YAGEO", "AC": "YAGEO",
    "CRCW": "Vishay",
    "ERJ": "Panasonic", "EXB": "Panasonic", "ERZ": "Panasonic",
    "MCR": "ROHM",
    "MMA": "Vishay", "MMU": "Vishay", "MMB": "Vishay", "SMM": "Vishay",
}

_COMPETITOR_PARSERS = (parse_koa, parse_yageo, parse_vishay, parse_panasonic)


def _parse_out_of_scope(pn: str):
    for prefix in OUT_OF_SCOPE_PREFIXES + MELF_PREFIXES:
        if pn.startswith(prefix):
            return ParsedPN(status_jp="厚膜/対象外", maker=_OUT_OF_SCOPE_MAKER.get(prefix), series=prefix)
    return None


def parse_pn(pn: str) -> ParsedPN:
    """Normalize a raw part number and hand it to the matching parser."""
    normalized = normalize_pn(pn)

    # RG / RGV first: these go to reverse lookup
    rg = parse_rg(normalized)
    if rg:
        return rg

    oos = _parse_out_of_scope(normalized)
    if oos:
        return oos

    for parser in _COMPETITOR_PARSERS:
        parsed = parser(normalized)
        if parsed:
            return parsed

    return ParsedPN(status_jp="不明(コード未定義)")
