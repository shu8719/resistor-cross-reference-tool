import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from services.bulk_processor import build_bulk_excel_output

bulk_bp = Blueprint("bulk", __name__)


@bulk_bp.route("/upload_bulk", methods=["POST"])
def upload_bulk():
    try:
        file = request.files["file"]
        df = pd.read_excel(file, dtype=str)
    except Exception:
        return jsonify({"error": "Excel読込エラー"}), 400

    output = build_bulk_excel_output(df)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Susumu_Cross_Reference.xlsx",
    )

