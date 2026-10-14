const { createApp } = Vue;

const RECENT_KEY = "xref_recent";
const LANG_KEY = "xref_lang";
const RECENT_MAX = 5;
const PAGE_SIZE = 8;

// grade (API) -> status key used for colours / labels
const GRADE_STATUS = { "◎": "ok", "！": "warn", "×": "ng", "△": "unknown", REVERSE: "reverse" };
const STATUS_SYMBOL = { ok: "◎", warn: "！", ng: "×", unknown: "△", reverse: "⇄" };
const STEP_SYMBOL = { ok: "✓", ng: "✕", skip: "–", reverse: "⇄" };

const TEXTS = {
    ja: {
        tagline: "薄膜チップ抵抗 代替品番検索",
        language: "表示言語",
        tab_search: "品番検索",
        tab_bulk: "Excel一括解析",
        tab_specs: "対応品番・仕様",

        search_title: "品番から代替候補を探す",
        search_sub: "他社品番なら RG 代替候補を、RG / RGV 品番なら他社の相当品を表示します（自動判定）",
        placeholder: "例: RN73R1JTTD1002B25 / RG1608P-103-B-T5",
        clear: "クリア",
        analyze_btn: "解析する",
        samples: "サンプル",
        reverse_chip: "逆引き",

        status_ok: "代替候補あり",
        status_warn: "対応範囲外",
        status_ng: "対象外の品種",
        status_unknown: "形式不明",
        status_reverse: "逆引き",

        input_label: "入力品番：",
        thin_film: "（薄膜）",
        thick_film: "（厚膜）",
        reverse_note: "RG / RGV 品番を検出したため逆引きしました",

        recommended: "推奨品番",
        copy: "コピー",
        copied: "コピー済み",
        check_reverse: "逆引きで確認",
        spec_compare: "スペック比較",
        item: "項目",
        input_part: "入力品",
        proposed_part: "推奨品",
        verdict: "判定",
        verdict_match: "✓ 一致",
        verdict_equivalent: "✓ 同等",
        verdict_tighter: "✓ 同等（より厳しい）",
        verdict_differs: "！ 相違",
        breakdown: "入力品番の読み取り",
        breakdown_note: "青色の項目を代替候補の判定に使っています",

        spec_size: "サイズ",
        spec_res: "抵抗値",
        spec_tol: "公差",
        spec_tcr: "TCR",
        seg_series: "シリーズ",
        seg_size: "サイズ",
        seg_terminal: "端子",
        seg_packaging: "包装",
        seg_taping: "テーピング",
        seg_res: "抵抗値",
        seg_tol: "公差",
        seg_tcr: "TCR",
        seg_other: "その他",

        no_proposal_warn: "代替候補を提案できません",
        no_proposal_ng: "対象外の品種です",
        no_proposal_unknown: "品番の形式を判定できません",
        reason_prefix: "理由：",
        spec_check: "スペックと対応範囲",
        check_ok: "✓ 対応",
        check_ng: "✕ 範囲外",
        retry_title: "公差を変えて再検索",
        retry_case: "公差 ±{tol}% の場合",
        search_arrow: "検索 →",
        retry_note: "※ 公差だけを差し替えた入力品番の例です。実在する品番かはメーカー資料で確認してください",

        input_rg: "入力品番（RG / RGV シリーズ）",
        competitors: "他社の相当品",
        count: "{n}件",
        copy_list: "一覧をコピー",
        maker: "メーカー",
        series: "シリーズ",
        equivalent_pn: "相当品番",
        reverse_notice: "生成した相当品番が各社の製造レンジ内かは未検証です。発注前にメーカーの仕様書で確認してください。",
        no_competitors_title: "相当品番を生成できません",
        no_competitors_detail: "この組み合わせ（サイズ・公差・TCR）に対応する他社コードが見つかりませんでした。",

        empty_title: "品番を入力して解析すると、ここに結果が表示されます",
        empty_sub: "上のサンプルをクリックしても試せます",
        process: "判定プロセス",
        recent: "最近の検索",
        clear_all: "すべて消去",
        recent_empty: "まだ検索履歴はありません",

        bulk_title: "Excel一括解析",
        bulk_sub: "Excelをアップロードすると全行を判定し、結果列を追加したファイルを返します",
        download_xlsx: "結果をダウンロード（.xlsx）",
        drop_hint: "ファイルをドロップ、またはクリックして選択",
        drop_sub: ".xlsx ／ 品番列は自動で検出します",
        bulk_info: "{n}行を解析済み ・ 品番列「{col}」を自動検出",
        bulk_loading: "解析しています…",
        bulk_empty: "ファイルを選択すると、ここに解析結果の概要が表示されます",
        choose_other: "別のファイルを選ぶ",
        all: "すべて",
        filter_pn: "品番で絞り込み",
        row: "行",
        input_pn: "入力品番",
        maker_series: "メーカー / シリーズ",
        proposal_or_equiv: "推奨品番 / 相当品",
        note: "理由・メモ",
        equiv_count: "他社相当品 {n}件 →",
        reverse_sheet_note: "逆引きの結果は別シートに出力",
        no_rows: "該当する行がありません",
        range_of: "{from}–{to} 件目 ／ 全{total}件",
        bulk_error: "Excel の読み込みに失敗しました。.xlsx ファイルを確認してください。",
        download_error: "ダウンロードに失敗しました。",

        specs_title: "対応品番・仕様",
        specs_sub: "このツールが解析できる品番形式と、判定結果の意味です",
        supported_parts: "対応している品番",
        example: "入力例",
        grade_meaning: "判定結果の意味",
        meaning: "意味",
        meaning_ok: "代替候補品番の提案あり",
        meaning_warn: "対応範囲外（サイズ・TCR・抵抗値・公差が非対応）",
        meaning_ng: "厚膜抵抗など、対象外の品種",
        meaning_unknown: "品番の形式が不明、またはコードが未定義",
        meaning_reverse: "RG / RGV 品番の入力を検出（他社相当品を表示）",
        notes: "注意事項",
        note_rgv: "代替候補の提案は RG シリーズのみ対応しています。RGV シリーズ（3225 サイズ・高抵抗）は包装コードテーブルが未整備のため、現状は「対応範囲外」になります。",
        note_tol: "公差は「同等またはより厳しい」ものだけを提案します（例: ±0.25% → ±0.1%）。±0.5% より緩い品番、RG の最小公差 ±0.02% より厳しい品番は「対応範囲外」になります。",
        note_verify: "生成した品番が各社の製造レンジ内かは未検証です。発注前にメーカーの仕様書で確認してください。",

        copied_toast: "クリップボードにコピーしました",
        copy_failed: "コピーできませんでした",
        net_error: "通信エラーが発生しました",
    },
    en: {
        tagline: "Thin film chip resistor cross-reference",
        language: "Language",
        tab_search: "Part Search",
        tab_bulk: "Excel Bulk",
        tab_specs: "Supported Parts",

        search_title: "Find a substitute from a part number",
        search_sub: "Competitor PN → RG substitute. RG / RGV PN → competitor equivalents (auto-detected)",
        placeholder: "e.g. RN73R1JTTD1002B25 / RG1608P-103-B-T5",
        clear: "Clear",
        analyze_btn: "Analyze",
        samples: "Samples",
        reverse_chip: "Reverse",

        status_ok: "Substitute found",
        status_warn: "Out of range",
        status_ng: "Out of scope",
        status_unknown: "Unknown format",
        status_reverse: "Reverse lookup",

        input_label: "Input: ",
        thin_film: " (thin film)",
        thick_film: " (thick film)",
        reverse_note: "RG / RGV part detected, showing competitor equivalents",

        recommended: "RECOMMENDED PART",
        copy: "Copy",
        copied: "Copied",
        check_reverse: "Check in reverse",
        spec_compare: "Spec comparison",
        item: "Item",
        input_part: "Input",
        proposed_part: "Proposed",
        verdict: "Result",
        verdict_match: "✓ Match",
        verdict_equivalent: "✓ Equivalent",
        verdict_tighter: "✓ Equivalent (tighter)",
        verdict_differs: "! Differs",
        breakdown: "How the input was read",
        breakdown_note: "Blue segments are used to decide the substitute",

        spec_size: "Size",
        spec_res: "Resistance",
        spec_tol: "Tolerance",
        spec_tcr: "TCR",
        seg_series: "Series",
        seg_size: "Size",
        seg_terminal: "Terminal",
        seg_packaging: "Packaging",
        seg_taping: "Taping",
        seg_res: "Resistance",
        seg_tol: "Tolerance",
        seg_tcr: "TCR",
        seg_other: "Other",

        no_proposal_warn: "No substitute can be proposed",
        no_proposal_ng: "Out-of-scope part type",
        no_proposal_unknown: "Part number format not recognized",
        reason_prefix: "Reason: ",
        spec_check: "Specs and supported range",
        check_ok: "✓ Supported",
        check_ng: "✕ Out of range",
        retry_title: "Retry with another tolerance",
        retry_case: "With ±{tol}% tolerance",
        search_arrow: "Search →",
        retry_note: "* Example part numbers with only the tolerance code swapped. Confirm they exist in the maker's catalog.",

        input_rg: "INPUT PART (RG / RGV SERIES)",
        competitors: "Competitor equivalents",
        count: "{n} parts",
        copy_list: "Copy list",
        maker: "Maker",
        series: "Series",
        equivalent_pn: "Equivalent part",
        reverse_notice: "Generated equivalents are not checked against each maker's manufacturing range. Confirm with the datasheet before ordering.",
        no_competitors_title: "No equivalent could be generated",
        no_competitors_detail: "No competitor code matches this combination of size, tolerance and TCR.",

        empty_title: "Enter a part number to see the result here",
        empty_sub: "You can also click a sample above",
        process: "Decision process",
        recent: "Recent searches",
        clear_all: "Clear all",
        recent_empty: "No searches yet",

        bulk_title: "Excel bulk analysis",
        bulk_sub: "Upload an Excel file to analyze every row and download it with result columns added",
        download_xlsx: "Download results (.xlsx)",
        drop_hint: "Drop a file here, or click to choose",
        drop_sub: ".xlsx / the part number column is detected automatically",
        bulk_info: "{n} rows analyzed · PN column “{col}” detected",
        bulk_loading: "Analyzing…",
        bulk_empty: "Choose a file to see a summary of the analysis here",
        choose_other: "Choose another file",
        all: "All",
        filter_pn: "Filter by part number",
        row: "Row",
        input_pn: "Input PN",
        maker_series: "Maker / Series",
        proposal_or_equiv: "Proposed / Equivalent",
        note: "Reason / Note",
        equiv_count: "{n} competitor parts →",
        reverse_sheet_note: "Reverse lookups are written to a separate sheet",
        no_rows: "No matching rows",
        range_of: "{from}–{to} of {total}",
        bulk_error: "Could not read the Excel file. Please check it is a valid .xlsx.",
        download_error: "Download failed.",

        specs_title: "Supported parts & specs",
        specs_sub: "Part number formats this tool can analyze, and what each result means",
        supported_parts: "Supported part numbers",
        example: "Example",
        grade_meaning: "Result meanings",
        meaning: "Meaning",
        meaning_ok: "A substitute part number is proposed",
        meaning_warn: "Out of range (size, TCR, resistance or tolerance not supported)",
        meaning_ng: "Out of scope (thick film etc.)",
        meaning_unknown: "Unknown part number format or undefined code",
        meaning_reverse: "RG / RGV part detected (competitor equivalents shown)",
        notes: "Notes",
        note_rgv: "Substitutes are proposed for the RG series only. The RGV series (3225 size, high resistance) has no packaging code table yet, so it is reported as out of range.",
        note_tol: "Only equal-or-tighter tolerances are proposed (e.g. ±0.25% → ±0.1%). Parts looser than ±0.5% or tighter than the RG minimum ±0.02% are out of range.",
        note_verify: "Generated part numbers are not checked against each maker's manufacturing range. Confirm with the datasheet before ordering.",

        copied_toast: "Copied to clipboard",
        copy_failed: "Could not copy",
        net_error: "Connection error",
    },
};

function readJSON(key, fallback) {
    try {
        const v = JSON.parse(localStorage.getItem(key));
        return v == null ? fallback : v;
    } catch (e) {
        return fallback;
    }
}

function writeJSON(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        /* storage unavailable: ignore */
    }
}

createApp({
    data() {
        const params = new URLSearchParams(location.search);
        const view = ["search", "bulk", "specs"].includes(params.get("view")) ? params.get("view") : "search";
        return {
            view,
            lang: (params.get("lang") || readJSON(LANG_KEY, "ja")) === "en" ? "en" : "ja",
            tabs: [
                { key: "search", label: "tab_search" },
                { key: "bulk", label: "tab_bulk" },
                { key: "specs", label: "tab_specs" },
            ],
            samples: [
                { maker: "KOA", pn: "RN73R1JTTD1002B25" },
                { maker: "YAGEO", pn: "RT0402BRD071KL" },
                { maker: "Vishay", pn: "TNPW04021K00BEEA" },
                { maker: "Panasonic", pn: "ERA3ARB1002V" },
                { maker: "reverse", pn: "RG1608N-1002-B-T5" },
            ],
            supported: [
                { maker_jp: "KOA", maker_en: "KOA", series_jp: "RN73R / RN73H", series_en: "RN73R / RN73H", pn: "RN73R1JTTD1002B25" },
                { maker_jp: "YAGEO", maker_en: "YAGEO", series_jp: "RT", series_en: "RT", pn: "RT0402BRD071KL" },
                { maker_jp: "Vishay", maker_en: "Vishay", series_jp: "TNPW", series_en: "TNPW", pn: "TNPW04021K00BEEA" },
                { maker_jp: "Panasonic", maker_en: "Panasonic", series_jp: "ERA（A-type のみ）", series_en: "ERA (A-type only)", pn: "ERA3ARB1002V" },
                { maker_jp: "RG / RGV シリーズ", maker_en: "RG / RGV series", series_jp: "RG / RGV（逆引き）", series_en: "RG / RGV (reverse lookup)", pn: "RG1608N-1002-B-T5" },
            ],
            statusOrder: ["ok", "warn", "ng", "unknown", "reverse"],

            // search
            pn: params.get("pn") || "",
            result: null,
            resultKey: 0,
            loading: false,
            recent: readJSON(RECENT_KEY, []),
            copied: "",
            toast: "",

            // bulk
            bulk: null,
            bulkFile: null,
            bulkLoading: false,
            bulkDownloading: false,
            bulkFilter: "all",
            bulkQuery: "",
            bulkPage: 1,
            dragOver: false,
        };
    },

    computed: {
        status() {
            return this.result ? GRADE_STATUS[this.result.grade] || "unknown" : "unknown";
        },
        statusNote() {
            const r = this.result;
            if (!r) return "";
            if (r.mode === "reverse") return this.t("reverse_note");
            const name = r.maker_series || r.input_pn;
            const film = r.grade === "×" ? this.t("thick_film") : r.grade === "△" ? "" : this.t("thin_film");
            return this.t("input_label") + name + film;
        },
        noProposalTitle() {
            return this.t("no_proposal_" + this.status) || this.t("no_proposal_warn");
        },

        bulkCounts() {
            const counts = { ok: 0, warn: 0, ng: 0, unknown: 0, reverse: 0 };
            if (this.bulk) for (const r of this.bulk.rows) counts[this.gradeStatus(r.grade)]++;
            return counts;
        },
        filteredRows() {
            if (!this.bulk) return [];
            const q = this.bulkQuery.trim().toUpperCase();
            return this.bulk.rows.filter((r) => {
                if (this.bulkFilter !== "all" && this.gradeStatus(r.grade) !== this.bulkFilter) return false;
                if (q && !String(r.pn || "").toUpperCase().includes(q)) return false;
                return true;
            });
        },
        totalPages() {
            return Math.max(1, Math.ceil(this.filteredRows.length / PAGE_SIZE));
        },
        pagedRows() {
            const start = (this.bulkPage - 1) * PAGE_SIZE;
            return this.filteredRows.slice(start, start + PAGE_SIZE);
        },
        pageFrom() {
            return this.filteredRows.length ? (this.bulkPage - 1) * PAGE_SIZE + 1 : 0;
        },
        pageTo() {
            return Math.min(this.bulkPage * PAGE_SIZE, this.filteredRows.length);
        },
        pageItems() {
            const total = this.totalPages;
            const cur = this.bulkPage;
            if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
            const pages = new Set([1, 2, 3, total, cur - 1, cur, cur + 1].filter((p) => p >= 1 && p <= total));
            const sorted = [...pages].sort((a, b) => a - b);
            const items = [];
            for (let i = 0; i < sorted.length; i++) {
                if (i > 0 && sorted[i] - sorted[i - 1] > 1) items.push("…");
                items.push(sorted[i]);
            }
            return items;
        },
    },

    watch: {
        totalPages(n) {
            if (this.bulkPage > n) this.bulkPage = n;
        },
    },

    mounted() {
        if (this.pn && this.view === "search") this.analyze();
    },

    methods: {
        // ---------- i18n ----------
        t(key, params) {
            let s = TEXTS[this.lang][key];
            if (s == null) s = TEXTS.ja[key];
            if (s == null) return "";
            if (params) for (const [k, v] of Object.entries(params)) s = s.replace(`{${k}}`, v);
            return s;
        },
        // jp/en pair from the API: L(obj, "title") -> obj.title_jp | obj.title_en
        L(obj, field) {
            if (!obj) return "";
            const v = obj[`${field}_${this.lang === "en" ? "en" : "jp"}`];
            return v != null ? v : obj[`${field}_jp`] || "";
        },
        setLang(lang) {
            this.lang = lang;
            writeJSON(LANG_KEY, lang);
            document.documentElement.lang = lang;
        },

        // ---------- navigation ----------
        go(view) {
            this.view = view;
            this.syncUrl();
        },
        syncUrl() {
            const params = new URLSearchParams();
            if (this.view !== "search") params.set("view", this.view);
            if (this.view === "search" && this.result) params.set("pn", this.result.display_pn || this.pn);
            const qs = params.toString();
            history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
        },

        // ---------- status helpers ----------
        gradeStatus(grade) {
            return GRADE_STATUS[grade] || "unknown";
        },
        statusSymbol(status) {
            return STATUS_SYMBOL[status] || "△";
        },
        statusLabel(status) {
            return this.t("status_" + status);
        },
        stepSymbol(state) {
            return STEP_SYMBOL[state] || "–";
        },
        specLabel(key) {
            return this.t("spec_" + key);
        },
        segLabel(kind) {
            return this.t("seg_" + kind) || kind;
        },
        isKeySegment(kind) {
            return ["size", "res", "tol", "tcr"].includes(kind);
        },
        verdictLabel(v) {
            return this.t("verdict_" + v) || v;
        },

        // ---------- search ----------
        clearInput() {
            this.pn = "";
            this.result = null;
            this.syncUrl();
        },
        runSample(pn) {
            this.pn = pn;
            this.view = "search";
            this.analyze();
        },
        async analyze() {
            const pn = this.pn.trim();
            if (!pn || this.loading) return;
            this.loading = true;
            try {
                const res = await fetch("/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pn }),
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                this.result = await res.json();
                this.resultKey += 1;
                this.pushRecent(this.result.display_pn || pn, this.result.grade);
                this.syncUrl();
                if (window.scrollY > 120) window.scrollTo({ top: 0, behavior: "smooth" });
            } catch (e) {
                this.showToast(this.t("net_error"));
            } finally {
                this.loading = false;
            }
        },
        pushRecent(pn, grade) {
            const list = this.recent.filter((r) => r.pn !== pn);
            list.unshift({ pn, grade });
            this.recent = list.slice(0, RECENT_MAX);
            writeJSON(RECENT_KEY, this.recent);
        },
        clearRecent() {
            this.recent = [];
            writeJSON(RECENT_KEY, []);
        },

        // ---------- clipboard ----------
        async copy(text, token) {
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(text);
                } else {
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    ta.setAttribute("readonly", "");
                    ta.style.position = "fixed";
                    ta.style.opacity = "0";
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    document.body.removeChild(ta);
                }
                this.copied = token || text;
                this.showToast(this.t("copied_toast"));
                setTimeout(() => {
                    if (this.copied === (token || text)) this.copied = "";
                }, 1800);
            } catch (e) {
                this.showToast(this.t("copy_failed"));
            }
        },
        copyCompetitorList() {
            const lines = this.result.competitor_rows.map((r) => `${r.maker}\t${r.pn}`);
            this.copy(lines.join("\n"), "list");
        },
        showToast(msg) {
            this.toast = msg;
            clearTimeout(this._toastTimer);
            this._toastTimer = setTimeout(() => (this.toast = ""), 2000);
        },

        // ---------- bulk ----------
        pickFile() {
            this.$refs.fileInput && this.$refs.fileInput.click();
        },
        onFileChange(event) {
            const file = event.target.files && event.target.files[0];
            event.target.value = "";
            if (file) this.uploadBulk(file);
        },
        onDrop(event) {
            this.dragOver = false;
            const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
            if (file) this.uploadBulk(file);
        },
        async uploadBulk(file) {
            this.bulkLoading = true;
            const formData = new FormData();
            formData.append("file", file);
            try {
                const res = await fetch("/analyze_bulk", { method: "POST", body: formData });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                this.bulk = await res.json();
                this.bulkFile = file;
                this.bulkFilter = "all";
                this.bulkQuery = "";
                this.bulkPage = 1;
            } catch (e) {
                this.showToast(this.t("bulk_error"));
            } finally {
                this.bulkLoading = false;
            }
        },
        async downloadBulk() {
            if (!this.bulkFile) return;
            this.bulkDownloading = true;
            const formData = new FormData();
            formData.append("file", this.bulkFile);
            try {
                const res = await fetch("/upload_bulk", { method: "POST", body: formData });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                const now = new Date();
                const stamp = [now.getFullYear(), now.getMonth() + 1, now.getDate(), now.getHours(), now.getMinutes()]
                    .map((n) => String(n).padStart(2, "0"))
                    .join("");
                a.href = url;
                a.download = `CrossRef_Result_${stamp}.xlsx`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (e) {
                this.showToast(this.t("download_error"));
            } finally {
                this.bulkDownloading = false;
            }
        },
        setFilter(f) {
            this.bulkFilter = f;
            this.bulkPage = 1;
        },
        pct(n) {
            if (!this.bulk || !this.bulk.rows.length) return 0;
            return Math.round((n / this.bulk.rows.length) * 100);
        },
        competitorCount(r) {
            return r.competitors ? Object.keys(r.competitors).length : 0;
        },
        noteText(r) {
            const s = this.gradeStatus(r.grade);
            if (s === "ok") return "—";
            if (s === "reverse") return this.t("reverse_sheet_note");
            return this.L(r, "note") || "—";
        },
        noteClass(r) {
            const s = this.gradeStatus(r.grade);
            if (s === "ok") return "text-ink-3";
            if (s === "reverse") return "text-ink-2";
            return "text-status-" + s;
        },
        openFromBulk(pn) {
            this.runSample(pn);
        },
    },
}).mount("#app");
