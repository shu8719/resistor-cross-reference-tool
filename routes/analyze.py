from flask import Blueprint, jsonify, request

from services.analyzer import parse_pn, translate_status
from services.proposal_generator import generate_proposal
from services.reverse_lookup import generate_competitors
from utils.resistor_code import format_res

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    parsed = parse_pn(data["pn"])

    # Reverse mode (Susumu PN -> competitors)
    if parsed.is_reverse_mode:
        competitors = generate_competitors(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
        return jsonify(
            {
                "mode": "reverse",
                "grade": "REVERSE",
                "size": parsed.size,
                "res": format_res(parsed.res_ohm),
                "tol": f"±{parsed.tol_pct}%",
                "tcr": f"±{parsed.tcr_ppm} ppm/℃",
                "competitors": competitors,
                "reason_jp": "Susumu品番から他社相当品を検索しました。",
                "reason_en": "Searched competitor equivalents from Susumu PN.",
            }
        )

    status_en = translate_status(parsed.status_jp)

    # Strict out-of-scope
    if parsed.is_out_of_scope:
        return jsonify(
            {
                "mode": "normal",
                "grade": "×",
                "proposal": "対象外",
                "reason_jp": parsed.status_jp,
                "reason_en": f"Result: {status_en}",
                "size": "-",
                "res": "-",
                "tol": "-",
                "tcr": "-",
            }
        )

    if parsed.is_out_of_range:
        return jsonify(
            {
                "mode": "normal",
                "grade": "！",
                "proposal": "",
                "reason_jp": parsed.status_jp,
                "reason_en": f"Result: {status_en}",
                "size": parsed.size or "-",
                "res": format_res(parsed.res_ohm) if parsed.res_ohm is not None else "-",
                "tol": f"±{parsed.tol_pct}%" if parsed.tol_pct is not None else "-",
                "tcr": f"±{parsed.tcr_ppm} ppm/℃" if parsed.tcr_ppm is not None else "-",
            }
        )

    if parsed.is_unknown:
        return jsonify(
            {
                "mode": "normal",
                "grade": "△",
                "proposal": "",
                "reason_jp": parsed.status_jp,
                "reason_en": "Unknown PN",
                "size": "-",
                "res": "-",
                "tol": "-",
                "tcr": "-",
            }
        )

    grade, proposal, note_jp, note_en, _series = generate_proposal(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)

    reason_jp = f"解析: {parsed.status_jp}\n判定: {note_jp}" if grade == "◎" else note_jp
    reason_en = f"Analysis: {status_en}\nResult: {note_en}" if grade == "◎" else note_en
    return jsonify(
        {
            "mode": "normal",
            "grade": grade,
            "proposal": proposal,
            "size": parsed.size,
            "res": format_res(parsed.res_ohm),
            "tol": f"±{parsed.tol_pct}%",
            "tcr": f"±{parsed.tcr_ppm} ppm/℃",
            "reason_jp": reason_jp,
            "reason_en": reason_en,
        }
    )

