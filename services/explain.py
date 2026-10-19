"""Turn an Analysis into the explanation shown in the UI.

Everything here is derived from `analyze_pn`; it adds no matching rules.
Strings come in jp/en pairs so the frontend can switch languages without
another round-trip.
"""
from typing import Dict, List, Optional, Tuple

from data.specs import PANA_ERA_TOL_CODE, RG_SPECS, RG_TCR_ALLOWED, RGV_SPECS, RGV_TCR_ALLOWED, YAGEO_RT_TOL_CODE
from parsers import ParsedPN
from parsers.rg import parse_rg
from services.analyzer import (
    GRADE_OK,
    GRADE_OUT_OF_RANGE,
    GRADE_OUT_OF_SCOPE,
    GRADE_REVERSE,
    GRADE_UNKNOWN,
    REASON_MAKER_RANGE,
    Analysis,
    analyze_pn,
)
from services.proposal_generator import (
    REASON_PACKAGING,
    REASON_RANGE,
    REASON_SERIES,
    REASON_SIZE,
    REASON_TCR,
    REASON_TOL,
)
from utils.format import fmt_res, fmt_size, fmt_size_with_inch, fmt_tcr, fmt_tol
from utils.normalize import normalize_pn
from utils.resistor_code import is_e24, is_e96

# Tolerance code tables per maker, used to build "retry with another tolerance" PNs
MAKER_TOL_CODES: Dict[str, Dict[str, float]] = {
    "KOA": {"A": 0.05, "B": 0.1, "C": 0.25, "D": 0.5, "F": 1.0},
    "YAGEO": YAGEO_RT_TOL_CODE,
    "Vishay": {"B": 0.1, "D": 0.5, "F": 1.0},
    "Panasonic": PANA_ERA_TOL_CODE,
}
RETRY_TOLERANCES = (0.5, 0.1)

COMPETITOR_SERIES: Dict[str, str] = {"KOA": "RN73R", "YAGEO": "RT", "Vishay": "TNPW", "Panasonic": "ERA（A-type）"}


def spec_summary(p: ParsedPN) -> str:
    tcr = f"±{p.tcr_ppm} ppm" if p.tcr_ppm is not None else "-"
    return " / ".join([fmt_size(p.size), fmt_res(p.res_ohm), fmt_tol(p.tol_pct), tcr])


# ------------------------------------------------------------ out-of-range detail

def build_checks(parsed: ParsedPN, reason: Optional[str]) -> List[dict]:
    """Per-spec OK/NG rows for the 'specs and supported range' table."""
    size_ok = parsed.size is not None and (parsed.size in RG_SPECS or parsed.size in RGV_SPECS)
    if reason == REASON_SIZE:
        size_ok = False

    tol = parsed.tol_pct
    tol_ok = tol is not None and (0.02 - 1e-9) <= tol <= (0.5 + 1e-9)
    tol_note_jp, tol_note_en = "", ""
    if not tol_ok and tol is not None:
        if tol > 0.5:
            tol_note_jp, tol_note_en = "±0.5%より緩い", "looser than ±0.5%"
        else:
            tol_note_jp, tol_note_en = "±0.02%より厳しい", "tighter than ±0.02%"

    tcr_allowed = RGV_TCR_ALLOWED if parsed.size == "3225" else RG_TCR_ALLOWED
    tcr_ok = parsed.tcr_ppm is not None and parsed.tcr_ppm in tcr_allowed and reason != REASON_TCR

    res = parsed.res_ohm
    res_ok = res is not None and (is_e24(res) or is_e96(res))
    res_note_jp, res_note_en = "", ""
    if reason == REASON_SERIES or (res is not None and not res_ok):
        res_ok = False
        res_note_jp, res_note_en = "E24 / E96 系列外", "not an E24 / E96 value"
    elif reason == REASON_RANGE:
        res_ok = False
        res_note_jp, res_note_en = "製造レンジ外", "outside the manufacturing range"
    elif reason == REASON_MAKER_RANGE:
        res_ok = False
        res_note_jp, res_note_en = "メーカーのレンジ外・未定義", "outside the maker's range"

    return [
        {"key": "size", "value": fmt_size_with_inch(parsed.size), "ok": size_ok, "note_jp": "" if size_ok else "対応サイズ外", "note_en": "" if size_ok else "unsupported size"},
        {"key": "res", "value": fmt_res(res), "ok": res_ok, "note_jp": res_note_jp, "note_en": res_note_en},
        {"key": "tol", "value": fmt_tol(tol), "ok": tol_ok, "note_jp": tol_note_jp, "note_en": tol_note_en},
        {"key": "tcr", "value": fmt_tcr(parsed.tcr_ppm), "ok": tcr_ok, "note_jp": "" if tcr_ok else "対応 TCR 外", "note_en": "" if tcr_ok else "unsupported TCR"},
    ]


def build_reason(a: Analysis) -> dict:
    """Title and detail (jp/en) for the reason box."""
    p = a.parsed
    size, res, tol, tcr = fmt_size(p.size), fmt_res(p.res_ohm), fmt_tol(p.tol_pct), fmt_tcr(p.tcr_ppm)
    ms = p.maker_series or "このメーカー"
    ms_en = p.maker_series or "this maker"
    rg_or_rgv = "RGV" if p.size == "3225" else "RG"

    if a.grade == GRADE_OUT_OF_SCOPE:
        return {
            "title_jp": "厚膜抵抗など、対象外の品種です",
            "title_en": "Out-of-scope part type (e.g. thick film)",
            "detail_jp": f"このツールは薄膜チップ抵抗のみを対象にしています。{ms} は厚膜抵抗または MELF のため、代替候補は提案しません。",
            "detail_en": f"This tool only covers thin film chip resistors. {ms_en} is a thick film or MELF part, so no substitute is proposed.",
        }
    if a.grade == GRADE_UNKNOWN:
        return {
            "title_jp": "品番の形式を判定できません",
            "title_en": "The part number format could not be recognized",
            "detail_jp": f"{a.note_jp}。対応形式は KOA RN73R / RN73H、YAGEO RT、Vishay TNPW、Panasonic ERA（A-type）、RG / RGV です。桁数やコードを確認してください。",
            "detail_en": f"{a.note_en}. Supported formats are KOA RN73R / RN73H, YAGEO RT, Vishay TNPW, Panasonic ERA (A-type) and RG / RGV. Check the digits and codes.",
        }

    reason = a.reason
    if reason == REASON_TOL:
        if p.tol_pct is not None and p.tol_pct > 0.5:
            detail_jp = f"入力品の公差は {tol} です。代替候補は「同等またはより厳しい公差」に限り、±0.5%〜±0.02% の品番のみ提案します。"
            detail_en = f"The input tolerance is {tol}. Substitutes must be equal or tighter, so only ±0.5% to ±0.02% parts are proposed."
        else:
            detail_jp = f"入力品の公差 {tol} は RG シリーズの最小公差 ±0.02% より厳しいため、同等以上の公差で提案できません。"
            detail_en = f"The input tolerance {tol} is tighter than the RG minimum of ±0.02%, so no equal-or-tighter substitute exists."
        return {"title_jp": "公差が対応範囲外です", "title_en": "Tolerance is outside the supported range", "detail_jp": detail_jp, "detail_en": detail_en}
    if reason == REASON_TCR:
        allowed = "±25 / ±50" if p.size == "3225" else "±5 / ±10 / ±25 / ±50 / ±100"
        return {
            "title_jp": "TCR が対応範囲外です",
            "title_en": "TCR is outside the supported range",
            "detail_jp": f"入力品の TCR は {tcr} です。{rg_or_rgv} シリーズは {allowed} ppm/℃ に対応しています。",
            "detail_en": f"The input TCR is {tcr}. The {rg_or_rgv} series supports {allowed} ppm/℃.",
        }
    if reason == REASON_SIZE:
        return {
            "title_jp": "サイズが対応範囲外です",
            "title_en": "Size is outside the supported range",
            "detail_jp": f"入力品のサイズ {size} は RG シリーズ（0603 / 1005 / 1608 / 2012 / 3216）に対応していません。",
            "detail_en": f"The input size {size} is not covered by the RG series (0603 / 1005 / 1608 / 2012 / 3216).",
        }
    if reason == REASON_SERIES:
        return {
            "title_jp": "抵抗値が E24 / E96 系列外です",
            "title_en": "Resistance is not an E24 / E96 value",
            "detail_jp": f"入力品の抵抗値 {res} は E24 / E96 の標準値ではないため、提案できません。",
            "detail_en": f"The input resistance {res} is not a standard E24 / E96 value, so no substitute is proposed.",
        }
    if reason == REASON_PACKAGING:
        return {
            "title_jp": "包装コードが未整備です",
            "title_en": "Packaging code table is not available",
            "detail_jp": "RGV シリーズ（3225 サイズ・高抵抗）の包装コードテーブルが未整備のため、現状は提案できません。",
            "detail_en": "The RGV series (3225 size, high resistance) packaging table is not available yet, so no substitute is proposed.",
        }
    if reason == REASON_RANGE:
        return {
            "title_jp": "抵抗値が製造レンジ外です",
            "title_en": "Resistance is outside the manufacturing range",
            "detail_jp": f"入力品の抵抗値 {res} は、RG{size}（TCR {tcr}・公差 {tol}）の製造レンジ外です。",
            "detail_en": f"The input resistance {res} is outside the RG{size} manufacturing range for TCR {tcr} and tolerance {tol}.",
        }
    # REASON_MAKER_RANGE
    return {
        "title_jp": "入力品番がメーカーの製造レンジ外です",
        "title_en": "The input part is outside the maker's range",
        "detail_jp": f"{ms} の仕様上、この組み合わせ（{size} / {res} / {tol} / {tcr}）はレンジ外または未定義です。品番を確認してください。（{a.note_jp}）",
        "detail_en": f"According to {ms_en}'s specification, this combination ({size} / {res} / {tol} / {tcr}) is out of range or undefined. Please check the part number. ({a.note_en})",
    }


def short_reason(a: Analysis) -> Tuple[str, str]:
    """One-line reason (jp, en) for the bulk table, grade "！" only."""
    p = a.parsed
    reason = a.reason
    if reason == REASON_TOL:
        return f"公差対象外（{fmt_tol(p.tol_pct)}）", f"Tolerance not supported ({fmt_tol(p.tol_pct)})"
    if reason == REASON_TCR:
        return f"TCR 対象外（{fmt_tcr(p.tcr_ppm)}）", f"TCR not supported ({fmt_tcr(p.tcr_ppm)})"
    if reason == REASON_SIZE:
        return f"サイズ対象外（{fmt_size(p.size)}）", f"Size not supported ({fmt_size(p.size)})"
    if reason == REASON_SERIES:
        return f"抵抗値が E24 / E96 系列外（{fmt_res(p.res_ohm)}）", f"Resistance not E24 / E96 ({fmt_res(p.res_ohm)})"
    if reason == REASON_RANGE:
        return f"抵抗値が製造レンジ外（{fmt_res(p.res_ohm)}）", f"Resistance out of range ({fmt_res(p.res_ohm)})"
    if reason == REASON_PACKAGING:
        return "包装コード未整備（RGV）", "Packaging table not available (RGV)"
    return f"メーカーのレンジ外・未定義（{a.note_jp}）", f"Outside the maker's range ({a.note_en})"


def build_retry_options(a: Analysis) -> List[dict]:
    """Same PN with only the tolerance code swapped, kept only when it would yield a proposal."""
    p = a.parsed
    table = MAKER_TOL_CODES.get(p.maker or "")
    if not table or p.tol_span is None:
        return []
    code_for = {pct: code for code, pct in table.items()}
    start, end = p.tol_span
    options = []
    for target in RETRY_TOLERANCES:
        if p.tol_pct is not None and abs(p.tol_pct - target) < 1e-9:
            continue
        code = code_for.get(target)
        if code is None:
            continue
        candidate = a.normalized[:start] + code + a.normalized[end:]
        retry = analyze_pn(candidate)
        if retry.grade == GRADE_OK:
            options.append({"tol": target, "pn": candidate, "proposal": retry.proposal_pn})
    return options


def build_compare(parsed: ParsedPN, proposal: str) -> List[dict]:
    """Input vs. proposed part, row by row."""
    pp = parse_rg(normalize_pn(proposal))
    if pp is None:
        return []
    tighter = parsed.tol_pct is not None and pp.tol_pct is not None and pp.tol_pct < parsed.tol_pct - 1e-9
    return [
        {"key": "size", "input": fmt_size_with_inch(parsed.size), "proposal": fmt_size(pp.size), "verdict": "match" if parsed.size == pp.size else "differs"},
        {"key": "res", "input": fmt_res(parsed.res_ohm), "proposal": fmt_res(pp.res_ohm), "verdict": "match" if parsed.res_ohm == pp.res_ohm else "differs"},
        {"key": "tol", "input": fmt_tol(parsed.tol_pct), "proposal": fmt_tol(pp.tol_pct), "verdict": "tighter" if tighter else "equivalent"},
        {"key": "tcr", "input": fmt_tcr(parsed.tcr_ppm), "proposal": fmt_tcr(pp.tcr_ppm), "verdict": "match" if parsed.tcr_ppm == pp.tcr_ppm else "differs"},
    ]


# ------------------------------------------------------------------- steps

def _step(state: str, title_jp: str, title_en: str, detail_jp: str, detail_en: str) -> dict:
    return {"state": state, "title_jp": title_jp, "title_en": title_en, "detail_jp": detail_jp, "detail_en": detail_en}


def _not_executed(title_jp: str, title_en: str) -> dict:
    return _step("skip", title_jp, title_en, "実行されません", "Not executed")


def build_steps(a: Analysis, reason: Optional[dict] = None) -> List[dict]:
    p = a.parsed
    steps = [_step("ok", "1. 正規化", "1. Normalize", a.normalized, a.normalized)]

    if a.grade == GRADE_REVERSE:
        steps.append(_step("reverse", "2. RG / RGV 品番を検出", "2. RG / RGV part detected", "逆引きモードに切り替え", "Switched to reverse lookup"))
        steps.append(_step("ok", "3. スペック抽出", "3. Extract specs", spec_summary(p), spec_summary(p)))
        makers = list(a.competitors)
        if makers:
            steps.append(_step("ok", "4. 他社品番の生成", "4. Generate competitor parts", f"{'・'.join(makers)} の{len(makers)}件", f"{len(makers)} parts: {', '.join(makers)}"))
        else:
            steps.append(_step("ng", "4. 他社品番の生成", "4. Generate competitor parts", "相当品を生成できません", "No equivalent could be generated"))
        return steps

    ms = p.maker_series
    if a.grade == GRADE_OUT_OF_SCOPE:
        steps.append(_step("ng", "2. メーカー判定", "2. Identify maker", f"{ms}（厚膜・対象外）" if ms else "厚膜・対象外", f"{ms} (thick film, out of scope)" if ms else "Thick film, out of scope"))
    elif p.is_unknown:
        steps.append(_step("ng", "2. メーカー判定", "2. Identify maker", f"{ms}（コード未定義）" if ms else "判定できません", f"{ms} (undefined code)" if ms else "Could not identify"))
    else:
        steps.append(_step("ok", "2. メーカー判定", "2. Identify maker", f"{ms}（薄膜）", f"{ms} (thin film)"))

    if p.has_specs:
        steps.append(_step("ok", "3. スペック抽出", "3. Extract specs", spec_summary(p), spec_summary(p)))
    else:
        steps.append(_not_executed("3. スペック抽出", "3. Extract specs"))

    if a.grade == GRADE_OK:
        series = a.proposal.series
        steps.append(_step("ok", "4. 仕様範囲の確認", "4. Check supported range", f"{series}シリーズの範囲内", f"Within the {series} series range"))
        steps.append(_step("ok", "5. 代替候補の生成", "5. Generate substitute", a.proposal_pn, a.proposal_pn))
    elif a.grade == GRADE_OUT_OF_RANGE:
        steps.append(_step("ng", "4. 仕様範囲の確認", "4. Check supported range", reason["title_jp"], reason["title_en"]))
        steps.append(_not_executed("5. 代替候補の生成", "5. Generate substitute"))
    else:
        steps.append(_not_executed("4. 仕様範囲の確認", "4. Check supported range"))
        steps.append(_not_executed("5. 代替候補の生成", "5. Generate substitute"))
    return steps


# ------------------------------------------------------------------ report

def build_report(raw_pn: str) -> dict:
    """Full /analyze payload for one part number."""
    a = analyze_pn(raw_pn)
    p = a.parsed
    report = {
        "input_pn": a.normalized,
        "display_pn": str(raw_pn).strip().upper() or a.normalized,
        "maker": p.maker,
        "series": p.series,
        "maker_series": p.maker_series,
        "segments": [{"text": t, "kind": k} for t, k in p.segments],
        "size": fmt_size(p.size),
        "res": fmt_res(p.res_ohm),
        "tol": fmt_tol(p.tol_pct),
        "tcr": fmt_tcr(p.tcr_ppm),
        "mode": "reverse" if a.grade == GRADE_REVERSE else "normal",
        "grade": a.grade,
    }

    if a.grade == GRADE_REVERSE:
        report["competitors"] = a.competitors
        report["competitor_rows"] = [{"maker": m, "series": COMPETITOR_SERIES.get(m, ""), "pn": pn} for m, pn in a.competitors.items()]
        report["steps"] = build_steps(a)
        return report

    if a.grade == GRADE_OK:
        report["proposal"] = a.proposal_pn
        report["compare"] = build_compare(p, a.proposal_pn)
        report["steps"] = build_steps(a)
        return report

    reason = build_reason(a)
    report["proposal"] = "対象外" if a.grade == GRADE_OUT_OF_SCOPE else ""
    report["reason"] = reason
    report["steps"] = build_steps(a, reason)
    if a.grade == GRADE_OUT_OF_RANGE:
        report["checks"] = build_checks(p, a.reason)
        report["retry_options"] = build_retry_options(a) if a.reason == REASON_TOL else []
    return report
