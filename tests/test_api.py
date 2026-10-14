import io

import pandas as pd
import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize(
    "pn, grade",
    [
        ("RN73R1JTTD1002B25", "◎"),
        ("RT0402BRD071KL", "◎"),
        ("TNPW04021K00BEEA", "◎"),
        ("ERA3ARB1002V", "◎"),
        ("RG1608N-1002-B-T5", "REVERSE"),
        ("CRCW04021K00FKEA", "×"),
        ("RT0402XXX999", "△"),
        ("rn73r-1j-ttd-1002-b-25", "◎"),  # normalisation
    ],
)
def test_sample_inputs(client, pn, grade):
    r = client.post("/analyze", json={"pn": pn})
    assert r.status_code == 200
    assert r.get_json()["grade"] == grade


@pytest.mark.parametrize(
    "pn",
    ["RN73R1JTTDRRRRB25", "RN73R1JTTD1R0RB25", "TNPW06031K0KBEEA", "RG1608N-RRR-B-T5"],
)
def test_malformed_resistance_does_not_crash(client, pn):
    r = client.post("/analyze", json={"pn": pn})
    assert r.status_code == 200
    assert r.get_json()["grade"] == "△"


def test_missing_pn_returns_400(client):
    r = client.post("/analyze", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_bulk_roundtrip(client):
    df = pd.DataFrame({"Part Number": ["RN73R1JTTD1002B25", None, "CRCW04021K00FKEA"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    r = client.post("/upload_bulk", data={"file": (buf, "in.xlsx")}, content_type="multipart/form-data")
    assert r.status_code == 200
    out = pd.read_excel(io.BytesIO(r.data))
    assert list(out["Match Grade"]) == ["◎", "△", "×"]
    assert out.loc[0, "Susumu Proposal"] == "RG1608P-103-B-T5"


def test_bulk_without_file_returns_400(client):
    r = client.post("/upload_bulk", data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_analyze_payload_explains_match(client):
    r = client.post("/analyze", json={"pn": "RN73R1JTTD1002B25"}).get_json()
    assert r["maker_series"] == "KOA RN73R"
    assert [s["kind"] for s in r["segments"]] == ["series", "size", "terminal", "packaging", "res", "tol", "tcr"]
    assert [s["state"] for s in r["steps"]] == ["ok"] * 5
    assert r["steps"][-1]["detail_jp"] == "RG1608P-103-B-T5"
    assert [c["key"] for c in r["compare"]] == ["size", "res", "tol", "tcr"]
    assert r["compare"][0]["input"] == "1608（0603）"
    assert all(c["verdict"] in ("match", "equivalent") for c in r["compare"])


def test_analyze_payload_explains_out_of_range_with_retry(client):
    r = client.post("/analyze", json={"pn": "RN73R1JTTD1002F25"}).get_json()
    assert r["grade"] == "！"
    assert r["reason"]["title_jp"] == "公差が対応範囲外です"
    checks = {c["key"]: c for c in r["checks"]}
    assert checks["tol"]["ok"] is False and checks["size"]["ok"] is True
    assert [s["state"] for s in r["steps"]] == ["ok", "ok", "ok", "ng", "skip"]
    retry = {o["tol"]: o["pn"] for o in r["retry_options"]}
    assert retry == {0.5: "RN73R1JTTD1002D25", 0.1: "RN73R1JTTD1002B25"}


def test_analyze_payload_reverse_rows(client):
    r = client.post("/analyze", json={"pn": "RG1608P-103-B-T5"}).get_json()
    assert r["grade"] == "REVERSE"
    assert r["display_pn"] == "RG1608P-103-B-T5"
    assert [row["maker"] for row in r["competitor_rows"]] == ["KOA", "YAGEO", "Vishay", "Panasonic"]
    assert r["steps"][1]["state"] == "reverse"


def test_analyze_payload_out_of_scope_and_unknown(client):
    r = client.post("/analyze", json={"pn": "CRCW04021K00FKEA"}).get_json()
    assert r["grade"] == "×" and r["maker_series"] == "Vishay CRCW"
    assert r["steps"][1]["state"] == "ng"
    r = client.post("/analyze", json={"pn": "RT0402XXX999"}).get_json()
    assert r["grade"] == "△" and r["reason"]["title_jp"] == "品番の形式を判定できません"


def test_bulk_json(client):
    df = pd.DataFrame({"MFR PN": ["RN73R1JTTD1002B25", None, "RG1608P-103-B-T5", "RC0603FR-0710KL", "ABC-1234-XYZ"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    r = client.post("/analyze_bulk", data={"file": (buf, "parts.xlsx")}, content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["filename"] == "parts.xlsx"
    assert body["pn_column"] == "MFR PN"
    assert body["row_count"] == 5
    assert [row["row"] for row in body["rows"]] == [2, 3, 4, 5, 6]
    assert [row["grade"] for row in body["rows"]] == ["◎", "△", "REVERSE", "×", "△"]
    assert body["rows"][0]["proposal"] == "RG1608P-103-B-T5"
    assert body["rows"][2]["competitors"]["KOA"] == "RN73R1JTTD1002B25"
    assert body["rows"][3]["maker_series"] == "YAGEO RC"
    assert body["rows"][4]["note_jp"] == "品番の形式を判定できません"


def test_bulk_json_short_reason_for_out_of_range(client):
    df = pd.DataFrame({"PN": ["RN73R1JTTD1002F25"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    r = client.post("/analyze_bulk", data={"file": (buf, "in.xlsx")}, content_type="multipart/form-data").get_json()
    assert r["rows"][0]["grade"] == "！"
    assert r["rows"][0]["note_jp"] == "公差対象外（±1%）"


def test_bulk_excel_has_reverse_sheet(client):
    df = pd.DataFrame({"Part Number": ["RG1608P-103-B-T5", "RN73R1JTTD1002B25"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    r = client.post("/upload_bulk", data={"file": (buf, "in.xlsx")}, content_type="multipart/form-data")
    sheets = pd.read_excel(io.BytesIO(r.data), sheet_name=None)
    assert list(sheets) == ["Results", "Reverse Lookup"]
    assert list(sheets["Results"]["Match Grade"]) == ["REVERSE", "◎"]
    rev = sheets["Reverse Lookup"]
    assert list(rev["Row"]) == [2]
    assert rev.loc[0, "KOA"] == "RN73R1JTTD1002B25"
