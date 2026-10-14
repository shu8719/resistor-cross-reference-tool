"""Build the human-readable explanation payload shown in the UI.

Everything here is derived from a ParsedPN plus the proposal result; it adds
no new matching rules.  Strings come in jp/en pairs so the frontend can switch
languages without another round-trip.
"""
from typing import Dict, List, Optional, Tuple

from data.susumu_specs import (
    PANA_ERA_TOL_CODE,
    SIZE_METRIC_TO_INCH,
    SUSUMU_SPECS_RG,
    SUSUMU_SPECS_RGV,
    SUSUMU_TCR_ALLOWED_RG,
    SUSUMU_TCR_ALLOWED_RGV,
    YAGEO_RT_TOL_CODE,
)
from parsers.susumu import parse_susumu
from services.analyzer import parse_pn, translate_status
from services.models import ParsedPN
from services.proposal_generator import generate_proposal
from services.reverse_lookup import generate_competitors
from utils.normalize import normalize_pn
from utils.resistor_code import format_res, is_e24, is_e96

# Tolerance code tables per maker, used to build "retry with another tolerance" PNs
MAKER_TOL_CODES: Dict[str, Dict[str, float]] = {
    "KOA": {"A": 0.05, "B": 0.1, "C": 0.25, "D": 0.5, "F": 1.0},
    "YAGEO": YAGEO_RT_TOL_CODE,
    "Vishay": {"B": 0.1, "D": 0.5, "F": 1.0},
    "Panasonic": PANA_ERA_TOL_CODE,
}
RETRY_TOLERANCES = (0.5, 0.1)

COMPETITOR_SERIES: Dict[str, str] = {"KOA": "RN73R", "YAGEO": "RT", "Vishay": "TNPW", "Panasonic": "ERA（A-type）"}


# ---------------------------------------------------------------- formatting

def fmt_size_with_inch(size: Optional[str]) -> str:
    if not size:
        return "-"
    inch = SIZE_METRIC_TO_INCH.get(size)
    return f"{size}（{inch}）" if inch else size


def fmt_res(res: Optional[float]) -> str:
    return format_res(res) if res is not None else "-"


def fmt_tol(tol: Optional[float]) -> str:
    return f"±{tol:g}%" if tol is not None else "-"


def fmt_tcr(tcr: Optional[int]) -> str:
    return f"±{tcr} ppm/℃" if tcr is not None else "-"


def spec_summary(p: ParsedPN) -> str:
    return " / ".join(
        [
            p.size or "-",
            fmt_res(p.res_ohm),
            fmt_tol(p.tol_pct),
            f"±{p.tcr_ppm} ppm" if p.tcr_ppm is not None else "-",
        ]
    )


def _has_specs(p: ParsedPN) -> bool:
    return p.res_ohm is not None and p.tol_pct is not None and p.tcr_ppm is not None


# ------------------------------------------------------------ failure kinds

def failure_kind(parsed: ParsedPN, note_jp: str) -> Optional[str]:
    """Classify why a proposal could not be made."""
    if parsed.is_out_of_range:
        return "maker_range"
    if "公差" in note_jp:
        return "tol"
    if "TCR" in note_jp:
        return "tcr"
    if "サイズ" in note_jp:
        return "size"
    if "系列" in note_jp:
        return "series"
    if "包装" in note_jp:
        return "packaging"
    if "レンジ" in note_jp:
        return "range"
    return None


def _tcr_allowed(p: ParsedPN):
    return SUSUMU_TCR_ALLOWED_RGV if p.size == "3225" else SUSUMU_TCR_ALLOWED_RG


def build_checks(parsed: ParsedPN, kind: Optional[str]) -> List[dict]:
    """Per-spec OK/NG rows for the 'specs and supported range' table."""
    size_ok = parsed.size is not None and (parsed.size in SUSUMU_SPECS_RG or parsed.size in SUSUMU_SPECS_RGV)
    if kind == "size":
        size_ok = False

    tol = parsed.tol_pct
    tol_ok = tol is not None and (0.02 - 1e-9) <= tol <= (0.5 + 1e-9)
    tol_note_jp, tol_note_en = "", ""
    if not tol_ok and tol is not None:
        if tol > 0.5:
            tol_note_jp, tol_note_en = "±0.5%より緩い", "looser than ±0.5%"
        else:
            tol_note_jp, tol_note_en = "±0.02%より厳しい", "tighter than ±0.02%"

    tcr_ok = parsed.tcr_ppm is not None and parsed.tcr_ppm in _tcr_allowed(parsed)
    if kind == "tcr":
        tcr_ok = False

    res = parsed.res_ohm
    res_ok = res is not None and (is_e24(res) or is_e96(res))
    res_note_jp, res_note_en = "", ""
    if kind == "series" or (res is not None and not res_ok):
        res_ok = False
        res_note_jp, res_note_en = "E24 / E96 系列外", "not an E24 / E96 value"
    elif kind == "range":
        res_ok = False
        res_note_jp, res_note_en = "製造レンジ外", "outside the manufacturing range"
    elif kind == "maker_range":
        res_ok = False
        res_note_jp, res_note_en = "メーカーのレンジ外・未定義", "outside the maker's range"

    return [
        {"key": "size", "value": fmt_size_with_inch(parsed.size), "ok": size_ok, "note_jp": "" if size_ok else "対応サイズ外", "note_en": "" if size_ok else "unsupported size"},
        {"key": "res", "value": fmt_res(res), "ok": res_ok, "note_jp": res_note_jp, "note_en": res_note_en},
        {"key": "tol", "value": fmt_tol(tol), "ok": tol_ok, "note_jp": tol_note_jp, "note_en": tol_note_en},
        {"key": "tcr", "value": fmt_tcr(parsed.tcr_ppm), "ok": tcr_ok, "note_jp": "" if tcr_ok else "対応 TCR 外", "note_en": "" if tcr_ok else "unsupported TCR"},
    ]


def build_reason(parsed: ParsedPN, kind: Optional[str], grade: str, note_jp: str) -> dict:
    size, res, tol, tcr = parsed.size or "-", fmt_res(parsed.res_ohm), fmt_tol(parsed.tol_pct), fmt_tcr(parsed.tcr_ppm)
    ms = parsed.maker_series or "このメーカー"
    ms_en = parsed.maker_series or "this maker"

    if grade == "×":
        return {
            "title_jp": "厚膜抵抗など、対象外の品種です",
            "title_en": "Out-of-scope part type (e.g. thick film)",
            "detail_jp": f"このツールは薄膜チップ抵抗のみを対象にしています。{ms} は厚膜抵抗または MELF のため、代替候補は提案しません。",
            "detail_en": f"This tool only covers thin film chip resistors. {ms_en} is a thick film or MELF part, so no substitute is proposed.",
        }
    if grade == "△":
        return {
            "title_jp": "品番の形式を判定できません",
            "title_en": "The part number format could not be recognized",
            "detail_jp": f"{note_jp}。対応形式は KOA RN73R / RN73H、YAGEO RT、Vishay TNPW、Panasonic ERA（A-type）、RG / RGV です。桁数やコードを確認してください。",
            "detail_en": f"{translate_status(note_jp)}. Supported formats are KOA RN73R / RN73H, YAGEO RT, Vishay TNPW, Panasonic ERA (A-type) and RG / RGV. Check the digits and codes.",
        }

    if kind == "tol":
        if parsed.tol_pct is not None and parsed.tol_pct > 0.5:
            detail_jp = f"入力品の公差は {tol} です。代替候補は「同等またはより厳しい公差」に限り、±0.5%〜±0.02% の品番のみ提案します。"
            detail_en = f"The input tolerance is {tol}. Substitutes must be equal or tighter, so only ±0.5% to ±0.02% parts are proposed."
        else:
            detail_jp = f"入力品の公差 {tol} は RG シリーズの最小公差 ±0.02% より厳しいため、同等以上の公差で提案できません。"
            detail_en = f"The input tolerance {tol} is tighter than the RG minimum of ±0.02%, so no equal-or-tighter substitute exists."
        return {"title_jp": "公差が対応範囲外です", "title_en": "Tolerance is outside the supported range", "detail_jp": detail_jp, "detail_en": detail_en}
    if kind == "tcr":
        allowed = "±25 / ±50" if parsed.size == "3225" else "±5 / ±10 / ±25 / ±50 / ±100"
        return {
            "title_jp": "TCR が対応範囲外です",
            "title_en": "TCR is outside the supported range",
            "detail_jp": f"入力品の TCR は {tcr} です。{'RGV' if parsed.size == '3225' else 'RG'} シリーズは {allowed} ppm/℃ に対応しています。",
            "detail_en": f"The input TCR is {tcr}. The {'RGV' if parsed.size == '3225' else 'RG'} series supports {allowed} ppm/℃.",
        }
    if kind == "size":
        return {
            "title_jp": "サイズが対応範囲外です",
            "title_en": "Size is outside the supported range",
            "detail_jp": f"入力品のサイズ {size} は RG シリーズ（0603 / 1005 / 1608 / 2012 / 3216）に対応していません。",
            "detail_en": f"The input size {size} is not covered by the RG series (0603 / 1005 / 1608 / 2012 / 3216).",
        }
    if kind == "series":
        return {
            "title_jp": "抵抗値が E24 / E96 系列外です",
            "title_en": "Resistance is not an E24 / E96 value",
            "detail_jp": f"入力品の抵抗値 {res} は E24 / E96 の標準値ではないため、提案できません。",
            "detail_en": f"The input resistance {res} is not a standard E24 / E96 value, so no substitute is proposed.",
        }
    if kind == "packaging":
        return {
            "title_jp": "包装コードが未整備です",
            "title_en": "Packaging code table is not available",
            "detail_jp": "RGV シリーズ（3225 サイズ・高抵抗）の包装コードテーブルが未整備のため、現状は提案できません。",
            "detail_en": "The RGV series (3225 size, high resistance) packaging table is not available yet, so no substitute is proposed.",
        }
    if kind == "range":
        return {
            "title_jp": "抵抗値が製造レンジ外です",
            "title_en": "Resistance is outside the manufacturing range",
            "detail_jp": f"入力品の抵抗値 {res} は、RG{size}（TCR {tcr}・公差 {tol}）の製造レンジ外です。",
            "detail_en": f"The input resistance {res} is outside the RG{size} manufacturing range for TCR {tcr} and tolerance {tol}.",
        }
    # maker_range / fallback
    return {
        "title_jp": "入力品番がメーカーの製造レンジ外です",
        "title_en": "The input part is outside the maker's range",
        "detail_jp": f"{ms} の仕様上、この組み合わせ（{size} / {res} / {tol} / {tcr}）はレンジ外または未定義です。品番を確認してください。（{note_jp}）",
        "detail_en": f"According to {ms_en}'s specification, this combination ({size} / {res} / {tol} / {tcr}) is out of range or undefined. Please check the part number. ({translate_status(note_jp)})",
    }


def short_reason(parsed: ParsedPN, kind: Optional[str], note_jp: str, note_en: str) -> Tuple[str, str]:
    """One-line reason for the bulk table (jp, en)."""
    if kind == "tol":
        return f"公差対象外（{fmt_tol(parsed.tol_pct)}）", f"Tolerance not supported ({fmt_tol(parsed.tol_pct)})"
    if kind == "tcr":
        return f"TCR 対象外（{fmt_tcr(parsed.tcr_ppm)}）", f"TCR not supported ({fmt_tcr(parsed.tcr_ppm)})"
    if kind == "size":
        return f"サイズ対象外（{parsed.size or '-'}）", f"Size not supported ({parsed.size or '-'})"
    if kind == "series":
        return f"抵抗値が E24 / E96 系列外（{fmt_res(parsed.res_ohm)}）", f"Resistance not E24 / E96 ({fmt_res(parsed.res_ohm)})"
    if kind == "range":
        return f"抵抗値が製造レンジ外（{fmt_res(parsed.res_ohm)}）", f"Resistance out of range ({fmt_res(parsed.res_ohm)})"
    if kind == "packaging":
        return "包装コード未整備（RGV）", "Packaging table not available (RGV)"
    if kind == "maker_range":
        return f"メーカーのレンジ外・未定義（{note_jp}）", f"Outside the maker's range ({translate_status(note_jp)})"
    return note_jp, note_en


def build_retry_options(parsed: ParsedPN, normalized: str) -> List[dict]:
    """Same PN with only the tolerance code swapped, kept only when it would yield a proposal."""
    table = MAKER_TOL_CODES.get(parsed.maker or "")
    if not table or parsed.tol_span is None:
        return []
    code_for = {pct: code for code, pct in table.items()}
    start, end = parsed.tol_span
    options = []
    for target in RETRY_TOLERANCES:
        if parsed.tol_pct is not None and abs(parsed.tol_pct - target) < 1e-9:
            continue
        code = code_for.get(target)
        if code is None:
            continue
        candidate = normalized[:start] + code + normalized[end:]
        cp = parse_pn(candidate)
        if cp.is_reverse_mode or cp.is_out_of_scope or cp.is_out_of_range or cp.is_unknown or not _has_specs(cp):
            continue
        grade, proposal, *_ = generate_proposal(cp.size, cp.res_ohm, cp.tol_pct, cp.tcr_ppm)
        if grade == "◎":
            options.append({"tol": target, "pn": candidate, "proposal": proposal})
    return options


def build_compare(parsed: ParsedPN, proposal: str) -> List[dict]:
    """Input vs. proposed part, row by row."""
    pp = parse_susumu(normalize_pn(proposal))
    if pp is None:
        return []
    rows = [
        {"key": "size", "input": fmt_size_with_inch(parsed.size), "proposal": pp.size or "-", "verdict": "match" if parsed.size == pp.size else "differs"},
        {"key": "res", "input": fmt_res(parsed.res_ohm), "proposal": fmt_res(pp.res_ohm), "verdict": "match" if parsed.res_ohm == pp.res_ohm else "differs"},
    ]
    if parsed.tol_pct is not None and pp.tol_pct is not None and pp.tol_pct < parsed.tol_pct - 1e-9:
        tol_verdict = "tighter"
    else:
        tol_verdict = "equivalent"
    rows.append({"key": "tol", "input": fmt_tol(parsed.tol_pct), "proposal": fmt_tol(pp.tol_pct), "verdict": tol_verdict})
    rows.append({"key": "tcr", "input": fmt_tcr(parsed.tcr_ppm), "proposal": fmt_tcr(pp.tcr_ppm), "verdict": "match" if parsed.tcr_ppm == pp.tcr_ppm else "differs"})
    return rows


# ------------------------------------------------------------------- steps

def _step(state: str, title_jp: str, title_en: str, detail_jp: str, detail_en: str) -> dict:
    return {"state": state, "title_jp": title_jp, "title_en": title_en, "detail_jp": detail_jp, "detail_en": detail_en}


def build_steps(parsed: ParsedPN, normalized: str, grade: str, proposal: str, reason: Optional[dict], competitors: Optional[dict] = None) -> List[dict]:
    steps = [_step("ok", "1. 正規化", "1. Normalize", normalized, normalized)]

    if parsed.is_reverse_mode:
        steps.append(_step("reverse", "2. RG / RGV 品番を検出", "2. RG / RGV part detected", "逆引きモードに切り替え", "Switched to reverse lookup"))
        steps.append(_step("ok", "3. スペック抽出", "3. Extract specs", spec_summary(parsed), spec_summary(parsed)))
        makers = list((competitors or {}).keys())
        if makers:
            steps.append(_step("ok", "4. 他社品番の生成", "4. Generate competitor parts", f"{'・'.join(makers)} の{len(makers)}件", f"{len(makers)} parts: {', '.join(makers)}"))
        else:
            steps.append(_step("ng", "4. 他社品番の生成", "4. Generate competitor parts", "相当品を生成できません", "No equivalent could be generated"))
        return steps

    ms = parsed.maker_series
    if parsed.is_out_of_scope:
        steps.append(_step("ng", "2. メーカー判定", "2. Identify maker", f"{ms}（厚膜・対象外）" if ms else "厚膜・対象外", f"{ms} (thick film, out of scope)" if ms else "Thick film, out of scope"))
    elif parsed.is_unknown:
        steps.append(_step("ng", "2. メーカー判定", "2. Identify maker", f"{ms}（コード未定義）" if ms else "判定できません", f"{ms} (undefined code)" if ms else "Could not identify"))
    else:
        steps.append(_step("ok", "2. メーカー判定", "2. Identify maker", f"{ms}（薄膜）", f"{ms} (thin film)"))

    if _has_specs(parsed):
        steps.append(_step("ok", "3. スペック抽出", "3. Extract specs", spec_summary(parsed), spec_summary(parsed)))
    else:
        steps.append(_step("skip", "3. スペック抽出", "3. Extract specs", "実行されません", "Not executed"))

    if grade == "◎":
        series = "RGV" if proposal.startswith("RGV") else "RG"
        steps.append(_step("ok", "4. 仕様範囲の確認", "4. Check supported range", f"{series}シリーズの範囲内", f"Within the {series} series range"))
        steps.append(_step("ok", "5. 代替候補の生成", "5. Generate substitute", proposal, proposal))
    elif grade == "！":
        steps.append(_step("ng", "4. 仕様範囲の確認", "4. Check supported range", reason["title_jp"] if reason else "対応範囲外", reason["title_en"] if reason else "Out of range"))
        steps.append(_step("skip", "5. 代替候補の生成", "5. Generate substitute", "実行されません", "Not executed"))
    else:
        steps.append(_step("skip", "4. 仕様範囲の確認", "4. Check supported range", "実行されません", "Not executed"))
        steps.append(_step("skip", "5. 代替候補の生成", "5. Generate substitute", "実行されません", "Not executed"))
    return steps


# ------------------------------------------------------------------ report

def _base(parsed: ParsedPN, normalized: str, raw_pn: str = "") -> dict:
    return {
        "input_pn": normalized,
        "display_pn": str(raw_pn).strip().upper() or normalized,
        "maker": parsed.maker,
        "series": parsed.series,
        "maker_series": parsed.maker_series,
        "segments": [{"text": t, "kind": k} for t, k in parsed.segments],
        "size": parsed.size or "-",
        "res": fmt_res(parsed.res_ohm),
        "tol": fmt_tol(parsed.tol_pct),
        "tcr": fmt_tcr(parsed.tcr_ppm),
    }


def build_report(raw_pn: str) -> dict:
    """Full /analyze payload for one part number."""
    parsed = parse_pn(raw_pn)
    normalized = normalize_pn(raw_pn)
    status_en = translate_status(parsed.status_jp)

    if parsed.is_reverse_mode:
        competitors = generate_competitors(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
        rows = [{"maker": m, "series": COMPETITOR_SERIES.get(m, ""), "pn": pn} for m, pn in competitors.items()]
        return {
            **_base(parsed, normalized, raw_pn),
            "mode": "reverse",
            "grade": "REVERSE",
            "competitors": competitors,
            "competitor_rows": rows,
            "reason_jp": "RG/RGV 品番を検出しました。各社相当品番を生成しました。",
            "reason_en": "Target-series part detected. Equivalent competitor parts generated.",
            "steps": build_steps(parsed, normalized, "REVERSE", "", None, competitors),
        }

    if parsed.is_out_of_scope:
        reason = build_reason(parsed, None, "×", parsed.status_jp)
        return {
            **_base(parsed, normalized, raw_pn),
            "mode": "normal",
            "grade": "×",
            "proposal": "対象外",
            "reason_jp": parsed.status_jp,
            "reason_en": f"Result: {status_en}",
            "reason": reason,
            "steps": build_steps(parsed, normalized, "×", "", reason),
        }

    if parsed.is_out_of_range:
        kind = "maker_range"
        reason = build_reason(parsed, kind, "！", parsed.status_jp)
        return {
            **_base(parsed, normalized, raw_pn),
            "mode": "normal",
            "grade": "！",
            "proposal": "",
            "reason_jp": parsed.status_jp,
            "reason_en": f"Result: {status_en}",
            "reason": reason,
            "checks": build_checks(parsed, kind),
            "retry_options": [],
            "steps": build_steps(parsed, normalized, "！", "", reason),
        }

    if parsed.is_unknown or not _has_specs(parsed):
        reason = build_reason(parsed, None, "△", parsed.status_jp)
        return {
            **_base(parsed, normalized, raw_pn),
            "mode": "normal",
            "grade": "△",
            "proposal": "",
            "reason_jp": parsed.status_jp,
            "reason_en": "Unknown PN",
            "reason": reason,
            "steps": build_steps(parsed, normalized, "△", "", reason),
        }

    grade, proposal, note_jp, note_en, _series = generate_proposal(parsed.size, parsed.res_ohm, parsed.tol_pct, parsed.tcr_ppm)
    if grade == "◎":
        reason_jp = f"解析: {parsed.status_jp}\n判定: {note_jp}"
        reason_en = f"Analysis: {status_en}\nResult: {note_en}"
        return {
            **_base(parsed, normalized, raw_pn),
            "mode": "normal",
            "grade": grade,
            "proposal": proposal,
            "reason_jp": reason_jp,
            "reason_en": reason_en,
            "compare": build_compare(parsed, proposal),
            "steps": build_steps(parsed, normalized, grade, proposal, None),
        }

    kind = failure_kind(parsed, note_jp)
    reason = build_reason(parsed, kind, grade, note_jp)
    return {
        **_base(parsed, normalized, raw_pn),
        "mode": "normal",
        "grade": grade,
        "proposal": proposal,
        "reason_jp": note_jp,
        "reason_en": note_en,
        "reason": reason,
        "checks": build_checks(parsed, kind),
        "retry_options": build_retry_options(parsed, normalized) if kind == "tol" else [],
        "steps": build_steps(parsed, normalized, grade, proposal, reason),
    }
