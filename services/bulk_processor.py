import io
from typing import Any, Dict, List, Optional

import pandas as pd

from services.analyzer import GRADE_OK, GRADE_OUT_OF_RANGE, GRADE_OUT_OF_SCOPE, GRADE_REVERSE, analyze_pn
from services.explain import short_reason
from utils.format import fmt_res, fmt_size, fmt_tcr, fmt_tol

COMPETITOR_MAKERS = ("KOA", "YAGEO", "Vishay", "Panasonic")


def pick_pn_column(df: pd.DataFrame) -> Optional[str]:
    """Column holding the part numbers: first one named like PN / PART, else the first column."""
    if len(df.columns) == 0:
        return None
    for c in df.columns:
        cu = str(c).upper()
        if ("PN" in cu) or ("PART" in cu):
            return c
    return df.columns[0]


def _row_note(a) -> tuple:
    if a.grade == GRADE_REVERSE:
        return "逆引き(別シート参照)", "Reverse lookup (see separate sheet)"
    if a.grade == GRADE_OUT_OF_SCOPE:
        return "厚膜抵抗のため対象外", "Thick film (out of scope)"
    if a.grade == GRADE_OUT_OF_RANGE:
        return short_reason(a)
    if a.grade == GRADE_OK:
        return a.note_jp, a.note_en
    return "品番の形式を判定できません", "Part number format not recognized"


def analyze_row(pn: Any) -> Dict[str, Any]:
    """Classify one part number for bulk output (Excel columns and JSON rows)."""
    if pn is None or (isinstance(pn, float) and pd.isna(pn)):
        pn = ""
    pn = str(pn).strip()
    a = analyze_pn(pn)
    p = a.parsed
    note_jp, note_en = _row_note(a)
    return {
        "pn": pn,
        "maker": p.maker,
        "series": p.series,
        "maker_series": p.maker_series,
        "grade": a.grade,
        "proposal": "対象外" if a.grade == GRADE_OUT_OF_SCOPE else a.proposal_pn,
        "note_jp": note_jp,
        "note_en": note_en,
        "size": fmt_size(p.size),
        "res": fmt_res(p.res_ohm),
        "tol": fmt_tol(p.tol_pct),
        "tcr": fmt_tcr(p.tcr_ppm),
        "competitors": a.competitors if a.grade == GRADE_REVERSE else None,
    }


def analyze_bulk_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """JSON-friendly rows for the bulk results table. `row` is the Excel row number (header = 1)."""
    col = pick_pn_column(df)
    return [{"row": i + 2, **analyze_row(row[col] if col is not None else "")} for i, (_, row) in enumerate(df.iterrows())]


def _results_sheet(df: pd.DataFrame, rows: List[Dict[str, Any]]) -> pd.DataFrame:
    results = pd.DataFrame(
        [
            {
                "Match Grade": r["grade"],
                "RG/RGV Proposal": r["proposal"],
                "Note": r["note_jp"],
                "Size": r["size"],
                "Res": r["res"],
                "Tol": r["tol"],
                "TCR": r["tcr"],
            }
            for r in rows
        ]
    )
    return pd.concat([df.reset_index(drop=True), results], axis=1)


def _reverse_sheet(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Competitor equivalents for every RG / RGV row."""
    reverse = [
        {"Row": r["row"], "Part Number": r["pn"], **{m: (r["competitors"] or {}).get(m, "") for m in COMPETITOR_MAKERS}}
        for r in rows
        if r["grade"] == GRADE_REVERSE
    ]
    return pd.DataFrame(reverse, columns=["Row", "Part Number", *COMPETITOR_MAKERS])


def build_bulk_excel_output(df: pd.DataFrame) -> io.BytesIO:
    rows = analyze_bulk_rows(df)
    reverse_df = _reverse_sheet(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _results_sheet(df, rows).to_excel(writer, index=False, sheet_name="Results")
        if not reverse_df.empty:
            reverse_df.to_excel(writer, index=False, sheet_name="Reverse Lookup")
    output.seek(0)
    return output
