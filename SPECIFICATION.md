# Susumu Cross-Reference Tool 仕様書

## 1. 文書概要

- 文書名: Susumu Cross-Reference Tool 仕様書
- 対象システム: `app.py` / `templates/index.html`
- 目的: 電子部品（薄膜チップ抵抗）品番の相互変換と適合判定を行う

## 2. システム概要

本システムは以下 2 方向のクロスリファレンスを提供する。

1. 他社品番 -> Susumu 推奨品番の提案（通常モード）
2. Susumu 品番 -> 他社相当品番の逆引き（逆引きモード）

Web UI から単体解析と Excel 一括解析を実行できる。

## 3. 技術構成

- バックエンド: Python / Flask / pandas / openpyxl
- フロントエンド: Vue 3 (CDN) / Tailwind CSS (CDN)
- テンプレート: Jinja2（Vue と競合回避のため `[[ ]]` 記法）

## 4. 主要機能

## 4.1 単体解析

- エンドポイント: `POST /analyze`
- 入力: JSON `{ "pn": "<品番>" }`
- 出力:
1. 通常モード結果（grade/proposal/reason/spec）
2. 逆引きモード結果（competitors）

## 4.2 一括解析

- エンドポイント: `POST /upload_bulk`
- 入力: Excel ファイル（multipart/form-data, key=`file`）
- 処理:
1. 行ごとに品番を抽出（列名に `PN` または `PART` を含む列を優先、なければ先頭列）
2. 単体解析と同等のロジックで判定
3. 元データに結果列を追加して Excel を返却
- 出力ファイル名: `Susumu_Cross_Reference.xlsx`

## 4.3 多言語表示

- UI 表示言語: 日本語 / 英語トグル
- API 返却は `reason_jp` と `reason_en` の両方を含む

## 5. 品番解析仕様

## 5.1 正規化

- 先頭末尾空白除去
- 英大文字化
- 英数字以外を除去（`-`, 空白などは除去）

## 5.2 判定フロー（優先順）

1. Susumu 形式判定（`RG` / `RGV`）
2. 対象外判定（厚膜/MELF 系プレフィックス）
3. KOA 判定（`RN73R`/`RN73H`）
4. YAGEO 判定（`RT...`）
5. Vishay 判定（`TNPW...`）
6. Panasonic 判定（`ERA...`）
7. 上記以外は `不明(コード未定義)`

## 5.3 ステータス分類

- `Susumu純正`: 逆引きモードへ遷移
- `薄膜(...)`: 通常モード提案対象
- `厚膜/対象外`: 提案対象外（grade=`×`）
- `範囲外(...)`: 仕様範囲外（grade=`！`）
- `不明(...)`: コード未定義/形式不一致（grade=`△`）

## 6. 通常モード（他社 -> Susumu）仕様

## 6.1 シリーズ選択

- 基本: `series = RG`
- 例外: サイズ `3225` の場合 `series = RGV`

## 6.2 入力条件

- サイズ、抵抗値、公差、TCR が抽出済みであること
- 抵抗値は E24 または E96 系列であること

## 6.3 TCR 制約

- RG 許容: `5, 10, 25, 50, 100`
- RGV 許容: `25, 50`

## 6.4 公差コード変換

- RG: `<=0.02:P`, `<=0.05:W`, `<=0.1:B`, `<=0.5:D`
- RGV: `<=0.1:B`, `<=0.5:D`

## 6.5 抵抗レンジ判定

- RG: `SUSUMU_SPECS_RG` テーブルを参照（サイズ x TCR x 公差コード）
- RGV: `SUSUMU_SPECS_RGV` テーブルを参照（サイズ x TCR）
- RG が範囲外でも、同サイズ/TCR で RGV が成立する場合は RGV 推奨へフォールバック

## 6.6 包装コード

- RG:
1. サイズ `0603` は `T10`
2. 公差 `D` は `T10`
3. それ以外は `T5`
- RGV:
1. `RGV_PACKAGING_TABLE` 参照
2. 未定義は `範囲外(RGV包装未定義)` 扱い

## 6.7 品番生成

生成形式:

`{series}{size}{tcr_code}-{res_code}-{tol_code}-{packaging}`

例:

`RG1608P-102-B-T5`

## 6.8 判定グレード

- `◎`: 提案成功
- `！`: 範囲外
- `×`: 厚膜/対象外
- `△`: 不明

## 7. 逆引きモード（Susumu -> 他社）仕様

`Susumu純正` 判定時に実行する。出力メーカーは以下。

1. KOA（RN73R）
2. YAGEO（RT）
3. Vishay（TNPW）
4. Panasonic（ERA）

各メーカー品番はサイズ、公差、TCR、抵抗値から規則変換で生成する。
条件に一致しないメーカーは出力に含めない。

## 8. API 仕様

## 8.1 `POST /analyze`

- Request JSON:
`{ "pn": "RN73R1JTTD1002B25" }`

- Response（通常モード例）:
`mode`, `grade`, `proposal`, `size`, `res`, `tol`, `tcr`, `reason_jp`, `reason_en`

- Response（逆引きモード例）:
`mode=reverse`, `grade=REVERSE`, `size`, `res`, `tol`, `tcr`, `competitors`, `reason_jp`, `reason_en`

## 8.2 `POST /upload_bulk`

- Request: multipart/form-data (`file`)
- Response: Excel バイナリ
- HTTP 400: Excel 読込エラー時

## 9. UI 仕様

- 入力欄: 品番 1 件入力
- 実行ボタン: `解析 / 逆引き (自動)`
- 結果表示:
1. 通常モード: Susumu 提案、グレード、抽出スペック、解析レポート
2. 逆引きモード: メーカー別相当品
- 一括アップロード: Excel ファイルを送信し、結果 Excel をダウンロード
- コピー機能: 提案品番・相当品番をクリップボードにコピー

## 10. エラー処理

- 通信失敗時: フロントでアラート表示
- Excel 読込失敗時: API が `{ "error": "Excel読込エラー" }` を返す
- 品番解釈失敗時: `不明(...)` として扱う

## 11. 既知制約・注意点

- `RGV_PACKAGING_TABLE` は初期状態で空であり、RGV 品番は包装未定義で範囲外になりやすい
- YAGEO の厳密パターンに一致しない `RT` 品番は `不明(コード未定義)` となる
- Panasonic は ERA A-type の strict 形式のみ提案対象
- 本実装はデータシート完全互換ではなく、コード内テーブルを正とする

## 12. 起動方法

1. 依存ライブラリをインストール（Flask, pandas, openpyxl）
2. `python3 app.py` を実行
3. `http://localhost:5000` にアクセス

## 13. 主な入出力ファイル

- 入力: ユーザー品番文字列、Excel（任意列）
- 出力:
1. 画面 JSON 結果
2. `Susumu_Cross_Reference.xlsx`（一括解析結果）

