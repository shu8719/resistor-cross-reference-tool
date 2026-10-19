import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from services.bulk_processor import analyze_bulk_rows, build_bulk_excel_output, pick_pn_column

bulk_bp = Blueprint("bulk", __name__)


def _read_upload():
    file = request.files.get("file")
    if file is None:
        return None, None, (jsonify({"error": "ファイルが指定されていません"}), 400)
    try:
        df = pd.read_excel(file, dtype=str)
    except Exception:
        return None, None, (jsonify({"error": "Excel読込エラー"}), 400)
    return file, df, None


@bulk_bp.route("/analyze_bulk", methods=["POST"])
def analyze_bulk():
    """JSON results for the on-screen table (the Excel download is a separate request)."""
    file, df, err = _read_upload()
    if err:
        return err
    rows = analyze_bulk_rows(df)
    col = pick_pn_column(df)
    return jsonify(
        {
            "filename": file.filename,
            "pn_column": None if col is None else str(col),
            "row_count": len(rows),
            "rows": rows,
        }
    )


@bulk_bp.route("/upload_bulk", methods=["POST"])
def upload_bulk():
    _file, df, err = _read_upload()
    if err:
        return err

    output = build_bulk_excel_output(df)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="CrossRef_Result.xlsx",
    )
