# お悔やみ情報自動取得・アップロードシステム

完全自動化されたお悔やみ情報の取得からGitHub Pagesへのアップロードまでのシステムです。

## 🚀 クイックスタート

### 1. ワンクリック実行（推奨）

```bash
auto_upload.bat
```

このバッチファイルを実行すると、以下の処理が自動で行われます：

1. **ネットから最新お悔やみ情報を取得**
2. **データの解析・構造化・フォーマット**  
3. **GitHub Pagesへの自動アップロード**

### 2. 初回設定

実行前に以下の設定を確認・変更してください：

#### a) GitHub Pagesリポジトリのパス設定

`auto_upload.bat`の先頭部分を環境に合わせて編集：

```batch
REM GitHub Pagesリポジトリのパスを設定（環境に合わせて変更）
set GITHUB_PAGES_REPO=%USERPROFILE%\your-github-pages-repo
```

#### b) WebDriverのパス確認

`selenium_okuyami_scraper.py`内のWebDriverパスを確認：

```python
edge_driver_path = r"%USERPROFILE%\OneDrive\Develop\temp\msedgedriver.exe"
```

## 📁 ファイル構成

```
okuyami/
├── auto_upload.bat                    # 🔥 メイン実行ファイル
├── selenium_okuyami_scraper.py        # ネット取得スクリプト
├── parse_and_format_obituary.py       # データ解析・フォーマット
├── upload_to_github_pages.py          # GitHub Pages アップロード
├── config_sample.ini                  # 設定ファイルサンプル
├── GitHub_Pages_Upload_README.md      # アップロード詳細マニュアル
├── okuyami_data/                      # 📥 取得データ格納フォルダ
│   └── okuyami_YYYYMMDD.txt
├── okuyami_output/                    # 📤 出力ファイル格納フォルダ
│   ├── *.csv                          # CSV形式
│   └── *.md                           # Markdown形式（GitHub Pages用）
```

## ⚙️ 個別実行方法

必要に応じて各スクリプトを個別に実行できます：

### 1. お悔やみ情報取得のみ

```bash
# 自動モード（最新1件）
python selenium_okuyami_scraper.py --auto

# 指定日
python selenium_okuyami_scraper.py --date 2025-08-06

# 最新5件
python selenium_okuyami_scraper.py --count 5

# ブラウザ表示モード（デバッグ用）
python selenium_okuyami_scraper.py --auto --no-headless
```

### 2. データ解析・フォーマットのみ

```bash
# 自動モード（最新ファイル）
python parse_and_format_obituary.py --auto

# 特定ファイル指定
python parse_and_format_obituary.py --file okuyami_data/okuyami_20250806.txt
```

### 3. GitHub Pagesアップロードのみ

```bash
# インタラクティブモード
python upload_to_github_pages.py

# コマンドライン指定
python upload_to_github_pages.py --repo "C:\path\to\github-pages-repo"
```

## 🔄 定期実行の設定

### Windowsタスクスケジューラでの自動実行

1. **タスクスケジューラを開く**
   ```
   Win + R → taskschd.msc
   ```

2. **基本タスクの作成**
   - 「基本タスクの作成」をクリック
   - 名前: "お悔やみ情報自動更新"
   - 説明: "毎日お悔やみ情報を取得してGitHub Pagesを更新"

3. **トリガー設定**
   - 「毎日」を選択
   - 開始時刻: 例）毎日 09:00

4. **操作設定**
   - 「プログラムの開始」を選択
   - プログラム/スクリプト: `C:\path\to\auto_upload.bat`
   - 開始場所: `%OneDrive%\Develop\okuyami` または `%USERPROFILE%\OneDrive\Develop\okuyami`

### cronでの自動実行（WSL/Linux）

```bash
# crontabを編集
crontab -e

# 毎日朝9時に実行
0 9 * * * cd /path/to/okuyami && ./auto_upload.bat
```

## 🛠️ トラブルシューティング

### よくある問題と対処法

#### 1. WebDriverエラー
```
Edge WebDriverが見つかりません
```
**対処法:**
- Edge WebDriverをダウンロード
- パスを正しく設定

#### 2. ログインエラー
```
ログインに失敗しました
```
**対処法:**
- メールアドレス・パスワードを確認
- 山梨日日新聞のサイト構造変更の可能性

#### 3. GitHub認証エラー
```
Authentication failed
```
**対処法:**
- GitHubトークンまたはSSH認証を確認
- `git push`が手動で実行できるか確認

#### 4. ファイルが見つからない
```
ファイルが見つかりません
```
**対処法:**
- 前の工程が正常に完了しているか確認
- ファイルパスが正しいか確認

### デバッグモード

問題の詳細を確認したい場合：

```bash
# ブラウザ表示でデバッグ
python selenium_okuyami_scraper.py --auto --no-headless

# 詳細ログ付きで実行
python upload_to_github_pages.py --repo "C:\path\to\repo" --message "デバッグ実行"
```

## 💾 ローカルファイル管理

### ファイル保存構造

```
okuyami_data/          # 取得データ
├── okuyami_20250806.txt
├── okuyami_20250805.txt
└── okuyami_20250804.txt

okuyami_output/        # 処理済みデータ
├── okuyami_20250806_parsed_20250806_173511.csv
├── okuyami_20250806_parsed_20250806_173511.md
├── okuyami_20250805_parsed_20250805_094722.csv
└── okuyami_20250805_parsed_20250805_094722.md
```

### 自動ファイル管理

- **重複回避**: 同日に複数回実行しても新しいタイムスタンプで保存
- **自動検出**: `--auto`フラグで最新ファイルを自動選択
- **履歴保持**: 過去のファイルは自動保持（手動削除まで）

## 📊 優先度ソート機能

お悔やみ情報は以下の優先度でソートされます：

1. **最優先**: ＮＥＣ/NEC キーワード含有
2. **次優先**: 中央市 在住
3. **通常**: その他

この順序で並べ替えられ、CSV・Markdown・GitHub Pagesすべてに適用されます。

## 📈 GitHub Pages履歴保持機能

### 自動履歴保持システム

このシステムは**履歴保持方式**を採用しており、実行するたびに新しい投稿として保存されます：

```
GitHub Pages投稿例:
├── 2025-08-06-okuyami-info.md  ← 本日の実行
├── 2025-08-05-okuyami-info.md  ← 昨日の実行
├── 2025-08-04-okuyami-info.md  ← 一昨日の実行
└── 2025-08-03-okuyami-info.md  ← 3日前の実行
```

### 履歴保持のメリット

1. **時系列追跡**: 日々の変化を確認可能
2. **検索性**: 特定日付の情報を後から参照
3. **比較機能**: 過去のデータとの比較分析
4. **バックアップ効果**: データの永続保存
5. **追悼の意味**: 故人の情報を大切に保持

### GitHub Pagesでの表示

- **最新投稿が上位**: 最新のお悔やみ情報が一番上に表示
- **アーカイブ機能**: 過去の投稿はアーカイブとして保持
- **カテゴリ分け**: `[obituary, news]` カテゴリで整理
- **タグ付け**: `[お悔やみ, 訃報, 山梨]` タグで検索可能

## 🔐 セキュリティ注意事項

- **ログイン情報**: スクリプト内のメールアドレス・パスワードは適切に管理
- **GitHubトークン**: 環境変数として設定推奨
- **自動実行**: セキュアな環境での実行を推奨

## 📝 ライセンス

このシステムはMITライセンスの下で公開されています。
- ✅ ログイン認証（OpenID対応）
- ✅ お悔やみ一覧の取得
- ✅ 個別記事の詳細情報取得
- ✅ ローカルファイルへの保存
- ✅ 日付指定での取得
- ✅ 複数件の一括取得

## 注意事項

### ログインについて
- 山梨日日新聞の有効なアカウント（メールアドレス・パスワード）が必要
- 会員限定コンテンツのため、ログインが必須
- OpenID認証システムに対応

### 利用制限
- サイトに負荷をかけないよう、リクエスト間隔（3秒）を設けています
- 大量取得時は時間がかかる場合があります
- サイトの利用規約を遵守してください

### セキュリティ
- ログイン情報はスクリプト内にハードコードされています
- 本番環境では環境変数や設定ファイルの使用を推奨
- ブラウザのセッション情報は自動的にクリーンアップされます

## トラブルシューティング

### 1. ChromeDriverエラーが発生する場合
```bash
# Chromiumのバージョンを確認
chromium-browser --version

# 対応するChromeDriverを再ダウンロード
# https://chromedriver.chromium.org/downloads
```

### 2. ログインエラーが発生する場合
- メールアドレス・パスワードを確認
- ブラウザ表示モード（`HEADLESS = False`）でデバッグ
- サイトの仕様変更の可能性

### 3. コンテンツが取得できない場合
- インターネット接続を確認
- サイトがメンテナンス中でないか確認
- ブラウザ表示モードで手動操作を確認

### 4. ファイル保存エラーが発生する場合
- 出力ディレクトリの書き込み権限を確認
- ディスク容量を確認

## デバッグ方法

### ブラウザ表示モードでの実行
```python
# ヘッドレスモードを無効にしてブラウザを表示
scraper = SeleniumOkuyamiScraper(
    email="your_email@example.com",
    password="your_password",
    output_dir="./okuyami_data",
    headless=False  # ブラウザが表示される
)
```

### ログ出力の確認
スクリプト実行時に以下の情報が出力されます：
- ブラウザ起動状況
- ログイン処理の進行状況
- お悔やみ情報の取得状況
- ファイル保存結果

## ライセンス
このスクリプトは教育・個人利用目的で作成されています。
商用利用や大量取得は避け、サイトの利用規約を遵守してください。

## 更新履歴
- v1.0: Seleniumを使用した初期版リリース
- v1.1: セレクタエラーの修正、ログイン処理の改善
- v1.2: エラーハンドリング強化、デバッグ機能追加

