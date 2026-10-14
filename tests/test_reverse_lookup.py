from services.reverse_lookup import generate_competitors


def test_sample_rg1608_matches_readme_samples():
    comp = generate_competitors("1608", 10000, 0.1, 10)
    assert comp["KOA"] == "RN73R1JTTD1002B10"
    assert comp["YAGEO"] == "RT0603BRB0710KL"
    assert comp["Vishay"] == "TNPW060310K0BYEA"
    assert comp["Panasonic"] == "ERA3ARB103V"


def test_vishay_high_resistance_codes():
    assert generate_competitors("1608", 47000, 0.1, 25)["Vishay"] == "TNPW060347K0BEEA"
    assert generate_competitors("1608", 100000, 0.1, 25)["Vishay"] == "TNPW0603100KBEEA"
    assert generate_competitors("1608", 1_000_000, 0.1, 25)["Vishay"] == "TNPW06031M00BEEA"


def test_yageo_fractional_code_uses_letter_as_point():
    assert generate_competitors("1608", 4700, 0.1, 25)["YAGEO"] == "RT0603BRD074K7L"


def test_panasonic_supports_0603_metric_via_era1a():
    comp = generate_competitors("0603", 1000, 0.1, 25)
    assert comp["Panasonic"] == "ERA1AEB102V"
