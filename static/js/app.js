const { createApp } = Vue;

createApp({
    data() {
        return {
            pn: "",
            result: null,
            loading: false,
            bulkLoading: false,
            lang: "ja", // デフォルト言語
            // 辞書データ
            texts: {
                ja: {
                    enter_pn: "品番を入力",
                    analyze_btn: "解析 / 逆引き (自動)",
                    hint_text: "他社品番 → 推奨品番変換 | RG/RGV 品番 → 他社逆引き (自動判定)",
                    bulk_upload: "一括アップロード (Excel)",
                    click_upload: "Excelファイルをアップロード",
                    susumu_proposal: "推奨品番",
                    competitor_xref: "他社相当品",
                    reverse_lookup: "逆引きモード",
                    analysis_report: "解析レポート",
                    bidirectional: "双方向検索",
                },
                en: {
                    enter_pn: "Enter Part Number",
                    analyze_btn: "Analyze / Reverse Lookup",
                    hint_text: "Competitor PN → Target Series | Target Series PN → Competitor (Auto Detect)",
                    bulk_upload: "Bulk Upload (Excel)",
                    click_upload: "Click to upload Excel",
                    susumu_proposal: "Recommended Part",
                    competitor_xref: "Competitor Equivalents",
                    reverse_lookup: "REVERSE MODE",
                    analysis_report: "Analysis Report",
                    bidirectional: "Bi-Directional Search",
                },
            },
        };
    },
    methods: {
        // 辞書ヘルパー
        t(key) {
            return this.texts[this.lang][key];
        },
        toggleLang() {
            this.lang = this.lang === "ja" ? "en" : "ja";
        },
        async analyze() {
            if (!this.pn) return;
            this.loading = true;
            this.result = null;

            try {
                const res = await fetch("/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pn: this.pn }),
                });
                await new Promise((r) => setTimeout(r, 400));
                this.result = await res.json();
            } catch (e) {
                alert("通信エラーが発生しました。/ Connection Error.");
            } finally {
                this.loading = false;
            }
        },
        async handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            this.bulkLoading = true;
            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await fetch("/upload_bulk", { method: "POST", body: formData });

                if (!response.ok) throw new Error("Server Error");

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                const now = new Date();
                const timeStr = `${now.getHours()}${now.getMinutes()}${now.getSeconds()}`;
                a.download = `CrossRef_Result_${timeStr}.xlsx`;

                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } catch (e) {
                alert("アップロード失敗。/ Upload Failed.");
            } finally {
                this.bulkLoading = false;
                event.target.value = "";
            }
        },
        setSample(pn) {
            this.pn = pn;
            this.analyze();
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text);
        },
    },
}).mount("#app");

