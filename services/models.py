from dataclasses import dataclass
from typing import Optional, Tuple

# A part-number segment: (text, kind). kind is one of
# series / size / terminal / packaging / taping / res / tol / tcr / other
Segment = Tuple[str, str]


@dataclass(frozen=True)
class ParsedPN:
    status_jp: str
    size: Optional[str] = None   # metric code like "1608"
    res_ohm: Optional[float] = None
    tol_pct: Optional[float] = None
    tcr_ppm: Optional[int] = None
    pkg_code: Optional[str] = None
    maker: Optional[str] = None      # "KOA", "YAGEO", "Vishay", "Panasonic"
    series: Optional[str] = None     # "RN73R", "RT", "TNPW", "ERA", "RG", "RGV"
    segments: Tuple[Segment, ...] = ()
    tol_span: Optional[Tuple[int, int]] = None  # position of the tolerance code in the normalized PN

    @property
    def is_reverse_mode(self) -> bool:
        return self.status_jp == "Susumu純正"

    @property
    def is_out_of_scope(self) -> bool:
        return ("厚膜" in self.status_jp) or ("MELF" in self.status_jp)

    @property
    def is_out_of_range(self) -> bool:
        return "範囲外" in self.status_jp

    @property
    def is_unknown(self) -> bool:
        return self.status_jp.startswith("不明")

    @property
    def maker_series(self) -> str:
        return " ".join(p for p in (self.maker, self.series) if p)
