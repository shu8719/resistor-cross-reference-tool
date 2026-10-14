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
