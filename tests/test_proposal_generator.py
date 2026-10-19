import pytest

from services.proposal_generator import (
    REASON_PACKAGING,
    REASON_RANGE,
    REASON_SERIES,
    REASON_SIZE,
    REASON_TCR,
    REASON_TOL,
    generate_proposal,
)


def test_readme_samples():
    assert generate_proposal("1608", 10000, 0.1, 25).pn == "RG1608P-103-B-T5"
    assert generate_proposal("1005", 1000, 0.1, 25).pn == "RG1005P-102-B-T5"
    assert generate_proposal("1608", 10000, 0.1, 10).pn == "RG1608N-103-B-T5"


def test_e96_value_uses_four_digit_code():
    assert generate_proposal("1608", 475000, 0.1, 25).pn == "RG1608P-4753-B-T5"


def test_tolerance_is_never_loosened():
    # ±0.25% must map to the tighter ±0.1% (B), not ±0.5% (D)
    p = generate_proposal("1608", 10000, 0.25, 25)
    assert p.grade == "◎"
    assert p.pn == "RG1608P-103-B-T5"
    assert p.reason is None


def test_tolerance_tighter_than_catalog_is_rejected():
    # RG tightest tolerance is ±0.02%; ±0.01% cannot be substituted
    p = generate_proposal("1608", 10000, 0.01, 25)
    assert (p.grade, p.pn, p.reason) == ("！", "", REASON_TOL)


def test_tolerance_over_half_percent_is_rejected():
    assert generate_proposal("1608", 10000, 1.0, 25).reason == REASON_TOL


@pytest.mark.parametrize(
    "size, res, tol, tcr, reason",
    [
        (None, 10000, 0.1, 25, REASON_SIZE),
        ("0402", 10000, 0.1, 25, REASON_SIZE),
        ("1608", 10000, 0.1, 15, REASON_TCR),
        ("3225", 200000, 0.1, 10, REASON_TCR),
        ("1608", 10001, 0.1, 25, REASON_SERIES),
        ("1608", 10, 0.1, 25, REASON_RANGE),
        ("3225", 200000, 0.1, 25, REASON_PACKAGING),
    ],
)
def test_rejections_carry_a_reason_code(size, res, tol, tcr, reason):
    p = generate_proposal(size, res, tol, tcr)
    assert p.grade == "！"
    assert p.reason == reason
