from services.proposal_generator import generate_proposal


def test_readme_samples():
    assert generate_proposal("1608", 10000, 0.1, 25)[1] == "RG1608P-103-B-T5"
    assert generate_proposal("1005", 1000, 0.1, 25)[1] == "RG1005P-102-B-T5"
    assert generate_proposal("1608", 10000, 0.1, 10)[1] == "RG1608N-103-B-T5"


def test_e96_value_uses_four_digit_code():
    assert generate_proposal("1608", 475000, 0.1, 25)[1] == "RG1608P-4753-B-T5"


def test_tolerance_is_never_loosened():
    # ±0.25% must map to the tighter ±0.1% (B), not ±0.5% (D)
    grade, proposal, *_ = generate_proposal("1608", 10000, 0.25, 25)
    assert grade == "◎"
    assert proposal == "RG1608P-103-B-T5"


def test_tolerance_tighter_than_catalog_is_rejected():
    # RG tightest tolerance is ±0.02%; ±0.01% cannot be substituted
    grade, proposal, note_jp, *_ = generate_proposal("1608", 10000, 0.01, 25)
    assert grade == "！"
    assert proposal == ""
    assert "公差" in note_jp


def test_tolerance_over_half_percent_is_rejected():
    grade, *_ = generate_proposal("1608", 10000, 1.0, 25)
    assert grade == "！"
