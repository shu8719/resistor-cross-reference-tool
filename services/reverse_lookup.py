import math
from typing import Dict

from data.susumu_specs import SIZE_METRIC_TO_INCH, SIZE_METRIC_TO_KOA
from utils.resistor_code import get_4digit_code, get_yageo_res_code, is_e24


def generate_competitors(size: str, res: float, tol: float, tcr: int) -> Dict[str, str]:
    results: Dict[str, str] = {}

    # 1) KOA RN73R
    koa_size = SIZE_METRIC_TO_KOA.get(size)
    if koa_size:
        koa_tol = {0.05: "A", 0.1: "B", 0.25: "C", 0.5: "D", 1.0: "F"}.get(tol)
        if koa_tol is not None:
            res_code = get_4digit_code(res)
            results["KOA"] = f"RN73R{koa_size}TTD{res_code}{koa_tol}{int(tcr)}"

    # 2) YAGEO RT
    inch_size = SIZE_METRIC_TO_INCH.get(size)
    if inch_size:
        yageo_tol = {0.01: "L", 0.05: "W", 0.1: "B", 0.25: "C", 0.5: "D", 1.0: "F"}.get(tol)
        yageo_tcr = {5: "A", 10: "B", 15: "C", 25: "D", 50: "E"}.get(tcr)
        if yageo_tol is not None and yageo_tcr is not None:
            yageo_res = get_yageo_res_code(res)
            results["YAGEO"] = f"RT{inch_size}{yageo_tol}R{yageo_tcr}07{yageo_res}L"

    # 3) Vishay TNPW
    if inch_size:
        vishay_tol = {0.1: "B", 0.5: "D", 1.0: "F"}.get(tol)
        vishay_tcr = {10: "Y", 15: "X", 25: "E", 50: "H"}.get(tcr)
        if vishay_tol is not None and vishay_tcr is not None:
            if res >= 1000:
                v_res = f"{res/1000:.2f}".replace(".", "K")
                if res == 1000:
                    v_res = "1K00"
                elif res == 10000:
                    v_res = "10K0"
            else:
                v_res = f"{res:.0f}R" if float(res).is_integer() else f"{res}R"
            results["Vishay"] = f"TNPW{inch_size}{v_res}{vishay_tol}{vishay_tcr}EA"

    # 4) Panasonic ERA
    pana_size_map = {"1608": "3", "2012": "6", "3216": "8"}
    p_s = pana_size_map.get(size) or ("2" if size == "1005" else None)
    if p_s:
        pana_tcr = {10: "R", 15: "P", 25: "E", 50: "H", 100: "K"}.get(tcr)
        pana_tol = {0.05: "W", 0.1: "B", 0.25: "C", 0.5: "D"}.get(tol)
        if pana_tcr is not None and pana_tol is not None:
            if is_e24(res):
                if res >= 10:
                    exp = int(math.floor(math.log10(res)))
                    mant = int(round(res / (10**exp) * 10))
                    p_res = f"{mant}{exp-1}"
                else:
                    p_res = f"{res}R"
            else:
                p_res = get_4digit_code(res)
            results["Panasonic"] = f"ERA{p_s}A{pana_tcr}{pana_tol}{p_res}V"

    return results

