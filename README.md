# お悔やみ情報パイプライン (okuyami)

このリポジトリは山梨日日新聞のお悔やみ情報を自動で取得・解析・整形し、GitHub Pages に公開するためのツール群を収めています。

主なスクリプト

- `selenium_okuyami_scraper.py` — Web から生テキストを取得して `okuyami_data/okuyami_YYYYMMDD.txt` に保存します（ログインが必要なページに対応）。
- `parse_and_format_obituary.py` — 生テキストまたは既存 CSV を解析して CSV / Markdown（GitHub Pages 用）を生成します。休刊日はプレースホルダを出力します。
- `upload_to_github_pages.py` — 生成した Markdown を Jekyll 形式に変換して GitHub Pages リポジトリへ add/commit/push します。
- `send_line_stats.py` — 集計結果を LINE (Messaging API) へ通知します（オプション）。
- `auto_upload.bat` / PowerShell スクリプト — 全工程（取得→解析→アップロード）をまとめて実行します。

フォルダ構成（抜粋）

```
okuyami/
├── okuyami_data/      # スクレイピングで保存した生テキスト
├── okuyami_output/    # 解析結果（CSV / Markdown）
├── _posts/             # (GitHub Pages リポジトリに同期される投稿)
├── selenium_okuyami_scraper.py
├── parse_and_format_obituary.py
├── upload_to_github_pages.py
└── GitHub_Pages_Upload_README.md  # アップロード詳細
```

クイックスタート

1. 設定
   - `config_sample.ini` を参照して `config.ini` を作成／編集してください。
   - （Windows）PowerShell の文字コードを UTF-8 に設定するとコミットメッセージの文字化けを防げます（例: `chcp 65001`）。

2. 取得（スクレイピング）

```powershell
python selenium_okuyami_scraper.py --auto
# or
python selenium_okuyami_scraper.py --date 2025-08-06
```

3. 解析（テキスト→CSV/MD）

```powershell
python parse_and_format_obituary.py --file okuyami_data/okuyami_20250806.txt --output-dir ./okuyami_output
# CSVからMarkdown生成
python parse_and_format_obituary.py --csv ./okuyami_output/okuyami_20250806_parsed_...csv --output-dir ./okuyami_output
```

4. アップロード（GitHub Pages）

```powershell
python upload_to_github_pages.py --repo "C:\path\to\okuyami-info"
```

休刊日の扱い

- `parse_and_format_obituary.py` は本文に `休刊日` や `掲載はありません` を検出すると、空のプレースホルダ CSV/MD (`*_holiday.csv` / `*_holiday.md`) を出力します。
- さらにオプションで空ポストを GitHub Pages に自動生成できます（`upload_to_github_pages.py --generate-empty` を使用）。

通知（運用）

- LINE 通知: `send_line_stats.py` を利用、設定は `config.ini` または環境変数で行います。
- Discord 通知: `common_utils.send_discord_alert()` を呼べるようにしてあります。環境変数 `DISCORD_WEBHOOK_URL` または `config.ini` の `[discord] webhook_url` で設定してください。

運用のヒント

- コミットの重複を避けるため、`upload_to_github_pages.py` は差分が無ければコミットをスキップする仕組みを持っています。
- PowerShell を使う場合、先頭で UTF-8 と LANG を設定することで git の文字化けを防げます。

トラブルシューティング（簡易）

- CSV 読込エラー: 文字コードを `utf-8-sig` で再読込してください。
- Git 認証エラー: SSH または Personal Access Token が正しく設定されているか確認してください。
- スクレイピング失敗: `--no-headless` でブラウザ表示モードにして、セレクタやログイン処理を目視デバッグしてください。

関連ドキュメント

- `GitHub_Pages_Upload_README.md` — GitHub Pages 側の設定とアップロード手順の詳細。Jekyll 設定例を含みます。
- `yamanashi_obituaries_selenium.md` または `山梨日日新聞お悔やみ情報取得スクリプト（Selenium版）.md` — 取得・運用ドキュメント（詳しいクイックスタートとトラブルシュート）。

コミットと共有

- 変更をリモートへ反映するには `git push origin main` を実行してください。

フィードバック／追加要望

- README に載せる重要な注意点や運用手順があれば指示ください。通知テスト（Discord/LINE）の手順を追記することもできます。
