import re


def normalize_pn(pn: str) -> str:
    raw = str(pn).strip()
    return re.sub(r"[^A-Z0-9]", "", raw.upper())

