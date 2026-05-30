# Thin Film Resistor Cross-Reference Tool

薄膜チップ抵抗の品番を相互変換する Flask 製 Web アプリケーション。  
電子部品の調達・設計変更時に、競合他社の品番からターゲットサプライヤーの代替品番を素早く特定できます。

## Overview

KOA・YAGEO・Vishay・Panasonic の薄膜チップ抵抗品番を入力すると、ターゲットサプライヤーの **RG / RGV シリーズ**から代替品番を自動提案します。  
逆方向（RG/RGV 品番 → 他社相当品）の逆引き検索にも対応しており、双方向の品番変換を 1 画面で行えます。

業務上の手作業によるクロスリファレンス作業（Excel 参照・手入力）をツール化し、単体解析・一括処理・多言語表示を統合した個人開発プロジェクトです。

## Features

- **単体解析** — 品番を 1 件入力し、抵抗値・公差・TCR を自動抽出してリアルタイム判定
- **逆引きモード** — RG/RGV 品番から KOA・YAGEO・Vishay・Panasonic の相当品を一覧表示
- **一括解析** — Excel ファイルをアップロードし、全行を一括処理した結果 Excel をダウンロード
- **多言語対応** — 画面表示を日本語 / 英語でトグル切替（API は `reason_jp` / `reason_en` を両方返却）
- **判定グレード** — マッチ品質を ◎ / ！ / × / △ で視覚化

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 / Flask |
| Data Processing | pandas / openpyxl |
| Frontend | Vue 3 (CDN) / Tailwind CSS (CDN) |
| Template Engine | Jinja2（`[[ ]]` 記法で Vue の `{{ }}` と競合回避） |

## Architecture

```
cross-reference/
├── app.py                     # Flask app factory・Blueprint 登録
├── routes/
│   ├── analyze.py             # POST /analyze — 単体解析エンドポイント
│   └── bulk.py                # POST /upload_bulk — 一括解析エンドポイント
├── services/
│   ├── analyzer.py            # 品番解析ディスパッチャ（パーサー呼び出し制御）
│   ├── models.py              # ParsedPN dataclass（解析結果モデル）
│   ├── proposal_generator.py  # RG/RGV 代替品番生成ロジック
│   ├── bulk_processor.py      # Excel 一括処理
│   └── reverse_lookup.py      # 逆引き品番生成
├── parsers/                   # メーカー別パーサー（各社独立モジュール）
│   ├── koa.py
│   ├── yageo.py
│   ├── vishay.py
│   ├── panasonic.py
│   └── susumu.py              # RG/RGV パーサー（逆引きモード検出）
├── data/
│   ├── susumu_specs.py        # 仕様テーブル・定数（RG/RGV 仕様・各社レンジ）
│   └── packaging.py           # 包装コードテーブル
├── utils/
│   ├── normalize.py           # 品番正規化（大文字化・記号除去）
│   └── resistor_code.py       # 抵抗値コード変換ユーティリティ
├── templates/index.html       # Vue 3 SPA
├── docs/images/               # スクリーンショット置き場
└── sample/
    └── sample_input.csv       # 入力フォーマットサンプル（架空データ）
```

**設計方針:** ルート（HTTP 処理）→ サービス（ビジネスロジック）→ パーサー（品番解析）→ ユーティリティ（純粋関数）の依存方向を一方向に保つ。

## Screenshots

> スクリーンショットは `docs/images/` に配置予定

## Setup

```bash
# 1. 依存ライブラリをインストール
pip install -r requirements.txt

# 2. 開発サーバー起動
python app.py
```

ブラウザで `http://localhost:5000` を開く。

### 動作確認用サンプル

`sample/sample_input.csv` に入力フォーマットのサンプルがあります（`.csv` → `.xlsx` に変換してからアップロード）。  
単体解析欄に以下の品番を直接入力しても動作確認できます。

| 品番 | メーカー | 期待される判定 |
|------|---------|--------------|
| `RN73R1JTTD1002B25` | KOA | ◎（代替品番を提案） |
| `RT0402BRD071KL` | YAGEO | ◎ |
| `TNPW04021K00BEEA` | Vishay | ◎ |
| `ERA3ARB1002V` | Panasonic | ◎ |
| `CRCW04021K00FKEA` | Vishay | ×（厚膜・対象外） |

## API Reference

### POST `/analyze`

品番を 1 件解析して JSON を返します。

```json
// Request
{ "pn": "RN73R1JTTD1002B25" }

// Response（通常モード — 代替品番あり）
{
  "mode": "normal",
  "grade": "◎",
  "proposal": "RG1608P-1002-B-T5",
  "size": "1608",
  "res": "10 kΩ",
  "tol": "±0.1%",
  "tcr": "±25 ppm/℃",
  "reason_jp": "解析: 薄膜(KOA RN73R)\n判定: RGシリーズ",
  "reason_en": "Analysis: Thin Film (KOA RN73R)\nResult: RG Series"
}
```

```json
// Response（逆引きモード — RG/RGV 品番入力時）
{
  "mode": "reverse",
  "grade": "REVERSE",
  "competitors": {
    "KOA": "RN73R1JTTD1002B25",
    "YAGEO": "RT0603BRD0710KL",
    "Vishay": "TNPW060310K0BEEA",
    "Panasonic": "ERA3ARB1002V"
  }
}
```

### POST `/upload_bulk`

Excel ファイル（`file` キー）を受け取り、判定結果列を追加した Excel を返します。

- 列名に `PN` または `PART` を含む列を品番列として使用（なければ先頭列）
- レスポンスファイル名: `Susumu_Cross_Reference.xlsx`

## Grade Reference

| Grade | 意味 |
|-------|------|
| ◎ | 代替品番の提案あり |
| ！ | 仕様範囲外（サイズ・TCR・抵抗値が非対応） |
| × | 厚膜抵抗・対象外品種 |
| △ | コード未定義・解析不可 |
| REVERSE | RG/RGV 純正品（逆引きモードへ遷移） |

## What I Learned

**1. Jinja2 と Vue 3 の変数記法の競合回避**  
両者がデフォルトで `{{ }}` を使うため、Flask アプリ初期化時に Jinja2 側の区切り文字を `[[ ]]` に変更して解決しました（`app.jinja_env.variable_start_string`）。SSR テンプレートエンジンとクライアントサイドフレームワークを共存させる際のパターンとして有効でした。

**2. パーサーの独立モジュール化**  
当初はすべてのメーカー判定ロジックを 1 ファイルに書いていましたが、各社パーサーを独立モジュールに分けることで可読性・テスト容易性が向上しました。`services/analyzer.py` は for ループで各パーサーを順に試すだけとなり、新メーカーの追加が 1 ファイル追加と 1 行の追記で完結します。

**3. frozen dataclass による解析結果の不変管理**  
`ParsedPN(frozen=True)` により、パース後の結果を不変オブジェクトとして扱えます。パーサー層・サービス層・ルート層の間でデータが改変されないことが保証され、デバッグ時の追跡が容易になりました。

**4. 浮動小数点誤差への対処**  
E24/E96 系列の抵抗値判定では `float == float` の比較が信頼できないため、仮数部を取り出して `math.isclose(rel_tol=1e-6)` で比較する方法を採用しました。

## Future Improvements

- **RGV 包装テーブルの実装** — `data/packaging.py` の `RGV_PACKAGING_TABLE` が空のため、RGV 品番の提案が現在「範囲外」扱いになる
- **共通解析ロジックの抽出** — `routes/analyze.py` と `services/bulk_processor.py` に同一の判定分岐が重複している。共通ヘルパー関数への切り出しで保守性が向上する
- **テストの追加** — 各パーサーと `utils/resistor_code.py` は純粋関数が多く、ユニットテストを追加しやすい
- **対応メーカーの拡張** — パーサーが独立モジュールのため、新メーカーの追加は新規ファイル 1 つで対応可能
