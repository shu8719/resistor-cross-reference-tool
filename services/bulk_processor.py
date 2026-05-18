import io

import pandas as pd

from services.analyzer import parse_pn
from services.proposal_generator import generate_proposal
from utils.resistor_code import format_res


def pick_pn_from_row(row: pd.Series) -> str:
    """Pick PN-like column from an uploaded row; fallback to the first column."""
    for c in row.index:
        cu = str(c).upper()
        if ("PN" in cu) or ("PART" in cu):
            return row[c]
    return row.iloc[0]


def process_bulk_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        pn = pick_pn_from_row(row)
        if pd.isna(pn):
            pn = ""

        parsed = parse_pn(pn)

        base_res = {
            "Match Grade": "△",
            "Susumu Proposal": "",
            "Note": "不明(コード未定義)",
            "Size": "-",
            "Res": "-",
            "Tol": "-",
            "TCR": "-",
        }

        if parsed.is_reverse_mode:
            base_res.update({"Match Grade": "-", "Susumu Proposal": str(pn), "Note": "Susumu品番(Skip)"})
        elif parsed.is_out_of_scope:
            base_res.update({"Match Grade": "×", "Susumu Proposal": "対象外", "Note": parsed.status_jp})
        elif parsed.is_out_of_range:
            base_res.update(
                {
                    "Match Grade": "！",
                    "Susumu Proposal": "",
                    "Note": parsed.status_jp,
                    "Size": parsed.size or "-",
                    "Res": format_res(parsed.res_ohm) if parsed.res_ohm is not None else "-",
                    "Tol": f"±{parsed.tol_pct}%" if parsed.tol_pct is not None else "-",
                    "TCR": f"±{parsed.tcr_ppm}" if parsed.tcr_ppm is not None else "-",
                }
            )
        elif not parsed.is_unknown:
            grade, proposal, note_jp, _note_en, _ = generate_proposal(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
            base_res.update(
                {
                    "Match Grade": grade,
                    "Susumu Proposal": proposal,
                    "Note": note_jp,
                    "Size": parsed.size,
                    "Res": format_res(parsed.res_ohm),
                    "Tol": f"±{parsed.tol_pct}%",
                    "TCR": f"±{parsed.tcr_ppm}",
                }
            )

        results.append(base_res)

    return pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)


def build_bulk_excel_output(df: pd.DataFrame) -> io.BytesIO:
    out_df = process_bulk_dataframe(df)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False)
    output.seek(0)
    return output

