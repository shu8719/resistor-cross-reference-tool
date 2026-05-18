from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ParsedPN:
    status_jp: str
    size: Optional[str] = None   # metric code like "1608"
    res_ohm: Optional[float] = None
    tol_pct: Optional[float] = None
    tcr_ppm: Optional[int] = None
    pkg_code: Optional[str] = None

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

