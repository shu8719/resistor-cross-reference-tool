import pytest

from utils.resistor_code import (
    get_vishay_res_code,
    get_yageo_res_code,
    parse_digit_code,
    parse_rkm_string,
)


@pytest.mark.parametrize(
    "val, expected",
    [
        (47, "47R0"),
        (100, "100R"),
        (1000, "1K00"),
        (4700, "4K70"),
        (4750, "4K75"),
        (10000, "10K0"),
        (47000, "47K0"),
        (100000, "100K"),
        (475000, "475K"),
        (1_000_000, "1M00"),
        (4_700_000, "4M70"),
    ],
)
def test_vishay_res_code_is_four_chars(val, expected):
    assert get_vishay_res_code(val) == expected


@pytest.mark.parametrize(
    "val, expected",
    [
        (47, "47R"),
        (100, "100R"),
        (1000, "1K"),
        (4700, "4K7"),
        (4750, "4K75"),
        (10000, "10K"),
        (47000, "47K"),
        (100000, "100K"),
        (1_000_000, "1M"),
    ],
)
def test_yageo_res_code_has_no_decimal_point(val, expected):
    assert get_yageo_res_code(val) == expected


@pytest.mark.parametrize("code", ["RRRR", "1R0R", "R", ""])
def test_parse_digit_code_returns_none_on_malformed(code):
    assert parse_digit_code(code) is None


@pytest.mark.parametrize("code", ["1K0K", "1M0K", "K", "1R0R"])
def test_parse_rkm_string_returns_none_on_malformed(code):
    assert parse_rkm_string(code) is None


def test_parse_digit_code_valid():
    assert parse_digit_code("1002") == 10000
    assert parse_digit_code("4R70") == pytest.approx(4.7)
    assert parse_digit_code("103") == 10000
