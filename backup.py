import math
import re
import io
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd

app = Flask(__name__)
app.jinja_env.variable_start_string = '[['
app.jinja_env.variable_end_string = ']]'

# --- 定数定義 ---

SUSUMU_SPECS_RG = {
    '0603': {5: (100, 3000), 100: (100, 56000)},
    '1005': {5: (100, 5100), 100: (47, 150000)},
    '1608': {5: (100, 10200), 100: (47, 1000000)},
    '2012': {5: (100, 33200), 100: (47, 2700000)},
    '3216': {5: (100, 33200), 100: (47, 5100000)}
}

SUSUMU_SPECS_RGV = {
    '1608': {100: (100000, 1000000)},
    '2012': {100: (100000, 2000000)},
    '3216': {100: (120000, 3000000)},
    '3225': {100: (120000, 4300000)}
}

SIZE_INCH_TO_METRIC = {
    '0201': '0603', '0402': '1005', '0603': '1608', '0805': '2012',
    '1206': '3216', '1210': '3225', '2010': '5025', '2512': '6432',
    '1218': '3246', '0100': '0402'
}
SIZE_METRIC_TO_INCH = {v: k for k, v in SIZE_INCH_TO_METRIC.items()}
SIZE_MAP_KOA = {'1E': '1005', '1J': '1608', '2A': '2012', '2B': '3216', '2E': '3225'}
SIZE_METRIC_TO_KOA = {v: k for k, v in SIZE_MAP_KOA.items()}
SIZE_MAP_PANA = {'1A': '0603', '2A': '1005', '2V': '1005', '3A': '1608', '3V': '1608', '6A': '2012', '6V': '2012', '8A': '3216', '8V': '3216'}
E24_VALUES = {1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1}

class CrossRefEngine:
    @staticmethod
    def format_res(val):
        if val >= 1000000: return f"{val/1000000:g} MΩ"
        if val >= 1000: return f"{val/1000:g} kΩ"
        return f"{val:g} Ω"

    @staticmethod
    def parse_rkm_string(res_str):
        res_str = res_str.upper()
        if 'K' in res_str: return float(res_str.replace('K', '.')) * 1000
        if 'M' in res_str: return float(res_str.replace('M', '.')) * 1000000
        if 'R' in res_str: return float(res_str.replace('R', '.'))
        return float(res_str)

    @staticmethod
    def parse_digit_code(res_str):
        if 'R' in res_str: return float(res_str.replace('R', '.'))
        digits = float(res_str[:-1])
        multiplier = 10 ** int(res_str[-1])
        return digits * multiplier

    @staticmethod
    def is_e24(val):
        if val <= 0: return False
        exponent = int(math.floor(math.log10(val)))
        mantissa = val / (10**exponent)
        for e24 in E24_VALUES:
            if math.isclose(mantissa, e24, rel_tol=0.005): return True
        if math.isclose(mantissa, 10.0, rel_tol=0.005): return True
        return False

    @staticmethod
    def get_susumu_res_code(val, size, series):
        """Generate Susumu nominal resistance code.

        Rules (per catalog):
          - RG: E24 -> 3 digit, E96 -> 4 digit, except RG3216 is always 4 digit.
          - RGV: always 4 digit.
        """
        use_4_digit = (series == 'RGV') or (size == '3216')

        def code_3digit_with_r(v: float) -> str:
            # Always 3 characters, using 'R' as decimal point.
            if v < 0:
                raise ValueError('resistance must be positive')
            if v < 1:
                # e.g. 0.10 -> R10, 0.47 -> R47
                n = int(round(v * 100))
                return f"R{n:02d}"
            if v < 10:
                i = int(v)
                d = int(round((v - i) * 10))
                # Handle carry (e.g. 9.95 -> 10.0) defensively
                if d == 10:
                    i += 1
                    d = 0
                if i >= 10:
                    # would exceed 3-digit-with-R format
                    return None
                return f"{i}R{d}"
            return None

        def code_4digit_with_r(v: float) -> str:
            # Always 4 characters, using 'R' as decimal point.
            if v < 0:
                raise ValueError('resistance must be positive')
            if v < 1:
                # e.g. 0.100 -> R100, 0.470 -> R470
                n = int(round(v * 1000))
                return f"R{n:03d}"
            if v < 10:
                i = int(v)
                d2 = int(round((v - i) * 100))
                if d2 == 100:
                    i += 1
                    d2 = 0
                if i >= 10:
                    return None
                return f"{i}R{d2:02d}"
            if v < 100:
                i = int(v)
                d1 = int(round((v - i) * 10))
                if d1 == 10:
                    i += 1
                    d1 = 0
                if i >= 100:
                    return None
                return f"{i:02d}R{d1}"
            return None

        # E24 path for RG 3-digit (except forced 4-digit cases)
        if (not use_4_digit) and CrossRefEngine.is_e24(val):
            rcode = code_3digit_with_r(val)
            if rcode is not None:
                return rcode
            exp = int(math.floor(math.log10(val)))
            mantissa = val / (10**exp)
            mant_2 = int(round(mantissa * 10))
            zeros = exp - 1
            return f"{mant_2}{zeros}"

        # 4-digit path (RGV or E96 or forced 4-digit RG3216)
        rcode4 = code_4digit_with_r(val)
        if rcode4 is not None:
            return rcode4
        exp = int(math.floor(math.log10(val)))
        mantissa = val / (10**exp)
        mant_3 = int(round(mantissa * 100))
        zeros = exp - 2
        return f"{mant_3}{zeros}"

    @staticmethod
    def get_4digit_code(val):
        if val < 100: return f"{val:.1f}".replace('.', 'R').ljust(4, '0')[:4]
        exp = int(math.floor(math.log10(val)))
        mantissa = val / (10**exp)
        mant_3 = int(round(mantissa * 100))
        zeros = exp - 2
        return f"{mant_3}{zeros}"

    @staticmethod
    def get_yageo_res_code(val):
        if val >= 1000000: return f"{val/1000000:g}M"
        if val >= 1000: return f"{val/1000:g}K"
        return f"{val:g}R"

    @staticmethod
    def generate_competitors(size, res, tol, tcr):
        results = {}
        # 1. KOA RN73R
        koa_size = SIZE_METRIC_TO_KOA.get(size)
        if koa_size:
            res_code = CrossRefEngine.get_4digit_code(res)
            koa_tol = {0.05:'A', 0.1:'B', 0.25:'C', 0.5:'D', 1.0:'F'}.get(tol, 'B')
            results['KOA'] = f"RN73R{koa_size}TTD{res_code}{koa_tol}{int(tcr)}"
        # 2. YAGEO RT
        inch_size = SIZE_METRIC_TO_INCH.get(size)
        if inch_size:
            yageo_tol = {0.01:'L', 0.05:'W', 0.1:'B', 0.25:'C', 0.5:'D', 1.0:'F'}.get(tol, 'B')
            yageo_tcr = {5:'A', 10:'B', 15:'C', 25:'D', 50:'E'}.get(tcr, 'D')
            yageo_res = CrossRefEngine.get_yageo_res_code(res)
            results['YAGEO'] = f"RT{inch_size}{yageo_tol}R{yageo_tcr}07{yageo_res}L"
        # 3. Vishay TNPW
        if inch_size:
            vishay_tol = {0.1:'B', 0.5:'D', 1.0:'F'}.get(tol, 'B')
            vishay_tcr = {10:'Y', 15:'X', 25:'E', 50:'H'}.get(tcr, 'E')
            if res >= 1000:
                v_res = f"{res/1000:.2f}".replace('.', 'K')
                if res == 1000: v_res = "1K00"
                elif res == 10000: v_res = "10K0"
            else:
                v_res = f"{res:.0f}R" if res.is_integer() else f"{res}R"
            results['Vishay'] = f"TNPW{inch_size}{v_res}{vishay_tol}{vishay_tcr}EA"
        # 4. Panasonic ERA
        pana_size_map = {'1608':'3', '2012':'6', '3216':'8'} 
        p_s = pana_size_map.get(size) or ('2' if size=='1005' else None)
        if p_s:
            pana_tcr = {10:'R', 15:'P', 25:'E', 50:'H', 100:'K'}.get(tcr, 'E')
            pana_tol = {0.05:'W', 0.1:'B', 0.25:'C', 0.5:'D'}.get(tol, 'B')
            if CrossRefEngine.is_e24(res):
                if res >= 10:
                    exp = int(math.floor(math.log10(res)))
                    mant = int(round(res / (10**exp) * 10))
                    p_res = f"{mant}{exp-1}"
                else: p_res = f"{res}R"
            else:
                p_res = CrossRefEngine.get_4digit_code(res)
            results['Panasonic'] = f"ERA{p_s}A{pana_tcr}{pana_tol}{p_res}V"
        return results

    @staticmethod
    def translate_status(status_jp):
        # 簡易翻訳マップ
        map_en = {
            "Susumu純正": "Susumu Original",
            "厚膜/対象外": "Thick Film (Out of Scope)",
            "MELF(対象外)": "MELF (Out of Scope)",
            "不明": "Unknown",
        }
        if status_jp in map_en: return map_en[status_jp]
        if "薄膜" in status_jp: return status_jp.replace("薄膜", "Thin Film")
        return status_jp

    @staticmethod
    def parse_pn(pn):
        raw_pn = str(pn).strip()
        pn = raw_pn.upper().replace(' ', '').replace('-', '')
        
        # 逆引き判定
        m_susumu = re.search(r'^(RG|RGV)(\d{4})([NPQRV])([0-9R]{3,4})([BDF])', pn)
        if m_susumu:
            series = m_susumu.group(1)
            size = m_susumu.group(2)
            tcr_code = m_susumu.group(3)
            res_str = m_susumu.group(4)
            tol_code = m_susumu.group(5)
            tcr = {'V':5, 'N':10, 'P':25, 'Q':50, 'R':100}.get(tcr_code, 25)
            tol = {'B':0.1, 'D':0.5, 'F':1.0}.get(tol_code, 0.1)
            if 'R' in res_str: res = float(res_str.replace('R', '.'))
            else:
                digits = int(res_str[:-1])
                multiplier = 10 ** int(res_str[-1])
                if len(res_str) == 3: res = digits * multiplier
                else: res = digits * multiplier
            return "Susumu純正", size, res, tol, tcr

        # 他社品番解析
        if pn.startswith(('UR73', 'WK73', 'SR73', 'KRL', 'RL', 'SR', 'RC', 'CRCW', 'ERJ', 'RK73', 'MCR', 'AC')):
            return "厚膜/対象外", None, None, None, None
        if pn.startswith(('MMA', 'MMU', 'MMB', 'SMM')):
            return "MELF(対象外)", None, None, None, None

        m_koa = re.search(r'RN73([HR])(1E|1J|2A|2B|2E)[A-Z]*([0-9R]{4})([ABCDF])([0-9]{2,3})', pn)
        if m_koa:
            size = SIZE_MAP_KOA.get(m_koa.group(2))
            res = CrossRefEngine.parse_digit_code(m_koa.group(3))
            tol = {'A':0.05, 'B':0.1, 'C':0.25, 'D':0.5, 'F':1.0}.get(m_koa.group(4), 0.5)
            tcr = int(m_koa.group(5))
            return f"薄膜(KOA RN73{m_koa.group(1)})", size, res, tol, tcr

        m_yageo = re.search(r'^(RT|AT)(\d{4})([BCDFLPW])([RK])([ABCDE])([0-9A-Z]{2})([0-9RKM]+)L?$', pn)
        if m_yageo:
            size = SIZE_INCH_TO_METRIC.get(m_yageo.group(2))
            tol = {'L':0.01, 'P':0.02, 'W':0.05, 'B':0.1, 'C':0.25, 'D':0.5, 'F':1.0}.get(m_yageo.group(3), 0.5)
            tcr = {'A':5, 'B':10, 'C':15, 'D':25, 'E':50}.get(m_yageo.group(5), 50)
            res = CrossRefEngine.parse_rkm_string(m_yageo.group(7))
            return f"薄膜(YAGEO {m_yageo.group(1)})", size, res, tol, tcr

        m_vishay = re.search(r'^TNPW(\d{4})([0-9RKM]+)([BDF])([HEXY])([A-Z0-9]{2})$', pn)
        if m_vishay:
            size = SIZE_INCH_TO_METRIC.get(m_vishay.group(1))
            res = CrossRefEngine.parse_rkm_string(m_vishay.group(2))
            tol = {'B':0.1, 'D':0.5, 'F':1.0}.get(m_vishay.group(3), 0.5)
            tcr = {'Y':10, 'X':15, 'E':25, 'H':50}.get(m_vishay.group(4), 50)
            return "薄膜(Vishay TNPW)", size, res, tol, tcr

        m_pana = re.search(r'^ERA([12368][AVK])([RPEHK])([WBCD])([0-9R]+)([A-Z]?)$', pn)
        if m_pana:
            size_code = m_pana.group(1)
            size = SIZE_MAP_PANA.get(size_code)
            tcr = {'R':10, 'P':15, 'E':25, 'H':50, 'K':100}.get(m_pana.group(2), 50)
            tol = {'W':0.05, 'B':0.1, 'C':0.25, 'D':0.5}.get(m_pana.group(3), 0.5)
            res = CrossRefEngine.parse_digit_code(m_pana.group(4))
            return f"薄膜(Panasonic ERA-{size_code[1]})", size, res, tol, tcr

        return "不明", None, None, None, None

    @staticmethod
    def generate_proposal(size, res, tol, tcr):
        series = 'RG'
        if size == '3225': series = 'RGV'
        
        if series == 'RG': spec = SUSUMU_SPECS_RG.get(size)
        else: spec = SUSUMU_SPECS_RGV.get(size)

        grade, note_jp, note_en = "◎", f"{series}シリーズ", f"{series} Series"
        
        if spec:
            check_key = 5 if tcr <= 5 else 100
            min_r, max_r = spec.get(check_key, (0, 0))
            if not (min_r <= res <= max_r):
                if series == 'RG' and size in SUSUMU_SPECS_RGV:
                    rgv_spec = SUSUMU_SPECS_RGV[size].get(100)
                    if rgv_spec and (rgv_spec[0] <= res <= rgv_spec[1]):
                        series = 'RGV'
                        note_jp = "RGV推奨(高抵抗)"
                        note_en = "RGV Recommended (High Res)"
                    else:
                        grade, note_jp, note_en = "！", f"{series}範囲外", f"Out of {series} Range"
                else:
                    grade, note_jp, note_en = "！", f"{series}範囲外", f"Out of {series} Range"
        elif size:
             grade, note_jp, note_en = "△", "サイズ対象外", "Size Not Supported"

        if tcr <= 5: s_tcr = 'V'
        elif tcr <= 10: s_tcr = 'N'
        elif tcr <= 25: s_tcr = 'P'
        elif tcr <= 50: s_tcr = 'Q'
        else: s_tcr = 'R'
        
        s_res = CrossRefEngine.get_susumu_res_code(res, size, series)
        s_tol = 'B' if tol <= 0.1 else ('D' if tol <= 0.5 else 'F') 
        
        proposal = f"{series}{size}{s_tcr}-{s_res}-{s_tol}-T5"
        return grade, proposal, note_jp, note_en, series

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    status, size, res, tol, tcr = CrossRefEngine.parse_pn(data['pn'])
    
    # 逆引きモード
    if status == "Susumu純正":
        competitors = CrossRefEngine.generate_competitors(size, res, tol, tcr)
        return jsonify({
            "mode": "reverse",
            "grade": "REVERSE",
            "size": size,
            "res": CrossRefEngine.format_res(res),
            "tol": f"±{tol}%",
            "tcr": f"±{tcr} ppm/℃",
            "competitors": competitors,
            "reason_jp": "Susumu品番から他社相当品を検索しました。",
            "reason_en": "Searched competitor equivalents from Susumu PN."
        })

    status_en = CrossRefEngine.translate_status(status)

    # 通常解析
    if "厚膜" in status or "MELF" in status:
        return jsonify({
            "mode":"normal", "grade": "×", "proposal": "対象外", 
            "reason_jp": f"判定: {status}", "reason_en": f"Result: {status_en}",
            "size":"-", "res":"-", "tol":"-", "tcr":"-"
        })
    if status == "不明":
        return jsonify({
            "mode":"normal", "grade": "△", "proposal": "", 
            "reason_jp": "解析不能", "reason_en": "Unknown PN",
            "size":"-", "res":"-", "tol":"-", "tcr":"-"
        })
    
    grade, proposal, note_jp, note_en, series = CrossRefEngine.generate_proposal(size, res, tol, tcr)
    
    return jsonify({
        "mode": "normal",
        "grade": grade, "proposal": proposal, "size": size,
        "res": CrossRefEngine.format_res(res), "tol": f"±{tol}%", "tcr": f"±{tcr} ppm/℃",
        "reason_jp": f"解析: {status}\n判定: {note_jp}",
        "reason_en": f"Analysis: {status_en}\nResult: {note_en}"
    })

@app.route('/upload_bulk', methods=['POST'])
def upload_bulk():
    try:
        file = request.files['file']
        df = pd.read_excel(file, dtype=str)
    except Exception:
        return jsonify({"error": "Excel読込エラー"}), 400

    results = []
    for _, row in df.iterrows():
        pn = next((row[c] for c in row.index if any(k in str(c).upper() for k in ['PN', 'PART'])), row.iloc[0])
        if pd.isna(pn): pn = ""
        
        status, size, res, tol, tcr = CrossRefEngine.parse_pn(pn)
        base_res = {"Match Grade": "△", "Susumu Proposal": "", "Note": "解析不能", "Size": "-", "Res": "-", "Tol": "-", "TCR": "-"}
        
        if status == "Susumu純正":
             base_res.update({"Match Grade": "-", "Susumu Proposal": pn, "Note": "Susumu品番(Skip)"})
        elif "厚膜" in status or "MELF" in status:
            base_res.update({"Match Grade": "×", "Susumu Proposal": "対象外", "Note": status})
        elif status != "不明":
            grade, proposal, note_jp, note_en, _ = CrossRefEngine.generate_proposal(size, res, tol, tcr)
            base_res.update({
                "Match Grade": grade, "Susumu Proposal": proposal, "Note": note_jp,
                "Size": size, "Res": CrossRefEngine.format_res(res),
                "Tol": f"±{tol}%", "TCR": f"±{tcr}"
            })
        results.append(base_res)

    out_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: out_df.to_excel(writer, index=False)
    output.seek(0)
    
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                     as_attachment=True, download_name="Susumu_Cross_Reference.xlsx")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
