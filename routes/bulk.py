import io

from flask import Blueprint, jsonify, request, send_file

from services.bulk_processor import analyze_bulk_rows, build_bulk_excel_output, cell_text, pick_pn_column, read_table

bulk_bp = Blueprint("bulk", __name__)


def _read_upload():
    file = request.files.get("file")
    if file is None:
        return None, None, (jsonify({"error": "ファイルが指定されていません"}), 400)
    try:
        table = read_table(io.BytesIO(file.read()))
    except Exception:
        return None, None, (jsonify({"error": "Excel読込エラー"}), 400)
    return file, table, None


@bulk_bp.route("/analyze_bulk", methods=["POST"])
def analyze_bulk():
    """JSON results for the on-screen table (the Excel download is a separate request)."""
    file, table, err = _read_upload()
    if err:
        return err
    header, data = table
    rows = analyze_bulk_rows(header, data)
    col = pick_pn_column(header)
    return jsonify(
        {
            "filename": file.filename,
            "pn_column": None if col is None else cell_text(header[col]),
            "row_count": len(rows),
            "rows": rows,
        }
    )


@bulk_bp.route("/upload_bulk", methods=["POST"])
def upload_bulk():
    _file, table, err = _read_upload()
    if err:
        return err

    output = build_bulk_excel_output(*table)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="CrossRef_Result.xlsx",
    )
