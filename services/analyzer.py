"""Classify one part number. Both the single-PN report and the bulk output start here."""
from dataclasses import dataclass, field
from typing import Dict, Optional

from parsers import ParsedPN, parse_pn
from services.proposal_generator import Proposal, generate_proposal
from services.reverse_lookup import generate_competitors
from utils.format import translate_status
from utils.normalize import normalize_pn

GRADE_OK = "◎"
GRADE_OUT_OF_RANGE = "！"
GRADE_OUT_OF_SCOPE = "×"
GRADE_UNKNOWN = "△"
GRADE_REVERSE = "REVERSE"

# Failure reason when the input itself is outside the maker's own range
REASON_MAKER_RANGE = "maker_range"


@dataclass(frozen=True)
class Analysis:
    normalized: str
    parsed: ParsedPN
    grade: str
    proposal: Optional[Proposal] = None       # set when the RG / RGV proposal step ran
    competitors: Dict[str, str] = field(default_factory=dict)  # reverse lookup only

    @property
    def reason(self) -> Optional[str]:
        """Why no substitute was proposed (grade "！" only)."""
        if self.grade != GRADE_OUT_OF_RANGE:
            return None
        return self.proposal.reason if self.proposal else REASON_MAKER_RANGE

    @property
    def proposal_pn(self) -> str:
        return self.proposal.pn if self.proposal else ""

    @property
    def note_jp(self) -> str:
        return self.proposal.note_jp if self.proposal else self.parsed.status_jp

    @property
    def note_en(self) -> str:
        return self.proposal.note_en if self.proposal else translate_status(self.parsed.status_jp)


def analyze_pn(raw_pn: str) -> Analysis:
    parsed = parse_pn(raw_pn)
    normalized = normalize_pn(raw_pn)

    if parsed.is_rg_series:
        competitors = generate_competitors(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
        return Analysis(normalized, parsed, GRADE_REVERSE, competitors=competitors)
    if parsed.is_out_of_scope:
        return Analysis(normalized, parsed, GRADE_OUT_OF_SCOPE)
    if parsed.is_out_of_range:
        return Analysis(normalized, parsed, GRADE_OUT_OF_RANGE)
    if parsed.is_unknown or not parsed.has_specs:
        return Analysis(normalized, parsed, GRADE_UNKNOWN)

    proposal = generate_proposal(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
    return Analysis(normalized, parsed, proposal.grade, proposal=proposal)
