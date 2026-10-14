from flask import Blueprint, jsonify, request

from services.explain import build_report

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    pn = data.get("pn")
    if not isinstance(pn, str) or not pn.strip():
        return jsonify({"error": "pn is required"}), 400
    return jsonify(build_report(pn))
