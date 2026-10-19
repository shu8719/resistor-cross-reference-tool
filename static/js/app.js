const { createApp } = Vue;

const RECENT_KEY = "xref_recent";
const LANG_KEY = "xref_lang";
const RECENT_MAX = 5;
const PAGE_SIZE = 8;

// grade (API) -> status key used for colours / labels
const GRADE_STATUS = { "◎": "ok", "！": "warn", "×": "ng", "△": "unknown", REVERSE: "reverse" };
const STATUS_SYMBOL = { ok: "◎", warn: "！", ng: "×", unknown: "△", reverse: "⇄" };
const STEP_SYMBOL = { ok: "✓", ng: "✕", skip: "–", reverse: "⇄" };

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
