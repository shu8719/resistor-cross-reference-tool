import io
from typing import Any, Dict, List, Optional

import pandas as pd

from services.analyzer import parse_pn, translate_status
from services.explain import failure_kind, short_reason
from services.proposal_generator import generate_proposal
from services.reverse_lookup import generate_competitors
from utils.resistor_code import format_res

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


def pick_pn_from_row(row: pd.Series) -> str:
    """Pick PN-like column from an uploaded row; fallback to the first column."""
    col = pick_pn_column(row.to_frame().T)
    return row[col] if col is not None else ""


def analyze_row(pn: Any) -> Dict[str, Any]:
    """Classify one part number for bulk output (Excel columns and JSON rows)."""
    if pn is None or (isinstance(pn, float) and pd.isna(pn)):
        pn = ""
    pn = str(pn).strip()
    parsed = parse_pn(pn)
    status_en = translate_status(parsed.status_jp)

    result: Dict[str, Any] = {
        "pn": pn,
        "maker": parsed.maker,
        "series": parsed.series,
        "maker_series": parsed.maker_series,
        "grade": "△",
        "proposal": "",
        "note_jp": "不明(コード未定義)",
        "note_en": "Unknown (Undefined Code)",
        "size": "-",
        "res": "-",
        "tol": "-",
        "tcr": "-",
        "competitors": None,
    }

    if parsed.is_reverse_mode:
        competitors = generate_competitors(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
        result.update(
            {
                "grade": "REVERSE",
                "note_jp": "逆引き(別シート参照)",
                "note_en": "Reverse lookup (see separate sheet)",
                "size": parsed.size,
                "res": format_res(parsed.res_ohm),
                "tol": f"±{parsed.tol_pct}%",
                "tcr": f"±{parsed.tcr_ppm} ppm/℃",
                "competitors": competitors,
            }
        )
    elif parsed.is_out_of_scope:
        result.update({"grade": "×", "proposal": "対象外", "note_jp": "厚膜抵抗のため対象外", "note_en": "Thick film (out of scope)"})
    elif parsed.is_out_of_range:
        note_jp, note_en = short_reason(parsed, "maker_range", parsed.status_jp, status_en)
        result.update(
            {
                "grade": "！",
                "note_jp": note_jp,
                "note_en": note_en,
                "size": parsed.size or "-",
                "res": format_res(parsed.res_ohm) if parsed.res_ohm is not None else "-",
                "tol": f"±{parsed.tol_pct}%" if parsed.tol_pct is not None else "-",
                "tcr": f"±{parsed.tcr_ppm} ppm/℃" if parsed.tcr_ppm is not None else "-",
            }
        )
    elif parsed.is_unknown or parsed.res_ohm is None or parsed.tol_pct is None or parsed.tcr_ppm is None:
        result.update({"note_jp": "品番の形式を判定できません", "note_en": "Part number format not recognized"})
    else:
        grade, proposal, note_jp, note_en, _ = generate_proposal(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
        if grade != "◎":
            note_jp, note_en = short_reason(parsed, failure_kind(parsed, note_jp), note_jp, note_en)
        result.update(
            {
                "grade": grade,
                "proposal": proposal,
                "note_jp": note_jp,
                "note_en": note_en,
                "size": parsed.size,
                "res": format_res(parsed.res_ohm),
                "tol": f"±{parsed.tol_pct}%",
                "tcr": f"±{parsed.tcr_ppm} ppm/℃",
            }
        )
    return result


def analyze_bulk_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """JSON-friendly rows for the bulk results table. `row` is the Excel row number (header = 1)."""
    col = pick_pn_column(df)
    rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        pn = row[col] if col is not None else ""
        rows.append({"row": i + 2, **analyze_row(pn)})
    return rows


def process_bulk_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for r in analyze_bulk_rows(df):
        results.append(
            {
                "Match Grade": r["grade"],
                "Susumu Proposal": r["proposal"],
                "Note": r["note_jp"],
                "Size": r["size"],
                "Res": r["res"],
                "Tol": r["tol"],
                "TCR": r["tcr"],
            }
        )
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)


def build_reverse_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """Second sheet: competitor equivalents for every RG / RGV row."""
    rows = []
    for r in analyze_bulk_rows(df):
        if r["grade"] != "REVERSE":
            continue
        comp = r["competitors"] or {}
        rows.append({"Row": r["row"], "Part Number": r["pn"], **{m: comp.get(m, "") for m in COMPETITOR_MAKERS}})
    return pd.DataFrame(rows, columns=["Row", "Part Number", *COMPETITOR_MAKERS])


def build_bulk_excel_output(df: pd.DataFrame) -> io.BytesIO:
    out_df = process_bulk_dataframe(df)
    reverse_df = build_reverse_sheet(df)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False, sheet_name="Results")
        if not reverse_df.empty:
            reverse_df.to_excel(writer, index=False, sheet_name="Reverse Lookup")
    output.seek(0)
    return output
