# GitHub Pages アップロードスクリプト

お悔やみ情報のMarkdownファイルをGitHub Pagesリポジトリに自動アップロードするスクリプトです。

## 機能

- 最新のMarkdownファイルを自動検出
- Jekyll形式の投稿ファイルに変換
- GitHub Pagesリポジトリに自動コミット・プッシュ
- インタラクティブモードとコマンドラインモードの両方に対応

## 前提条件

1. **GitHubリポジトリの準備**
   - GitHub Pagesが有効になっているリポジトリ
   - Jekyllサイトの設定（`_config.yml`など）
   - ローカルにcloneされたリポジトリ

### 📋 Jekyll設定ファイル（`_config.yml`）の作成

GitHub Pagesリポジトリのルートディレクトリに以下の`_config.yml`ファイルを作成してください：

```yaml
# サイト設定
title: "お悔やみ情報"
description: "山梨日日新聞のお悔やみ情報を自動収集・整理したサイトです"
url: "https://your-username.github.io"
baseurl: "/your-repository-name"

# 著者情報
author:
  name: "お悔やみ情報bot"
  email: "jun@taxa.jp"

# Jekyll設定
markdown: kramdown
highlighter: rouge
permalink: /:year/:month/:day/:title/

# テーマ設定（GitHub Pages対応）
theme: minima
# または remote_theme を使用
# remote_theme: jekyll/minima

# プラグイン（GitHub Pages対応のもの）
plugins:
  - jekyll-feed
  - jekyll-sitemap
  - jekyll-seo-tag

# コレクション設定
collections:
  posts:
    output: true
    permalink: /:collection/:year/:month/:day/:title/

# デフォルト設定
defaults:
  - scope:
      path: ""
      type: "posts"
    values:
      layout: "post"
      author: "お悔やみ情報bot"

# 除外ファイル
exclude:
  - README.md
  - Gemfile
  - Gemfile.lock
  - node_modules
  - vendor

# タイムゾーン
timezone: Asia/Tokyo

# 言語設定
lang: ja

# フィード設定
feed:
  categories:
    - obituary
    - news
```

### 📁 必要なディレクトリ構造

GitHub Pagesリポジトリに以下の構造を作成してください：

```
your-github-pages-repo/
├── _config.yml          # ← 上記の設定ファイル
├── _posts/              # ← 投稿ファイル用ディレクトリ（空でOK）
├── _layouts/            # ← レイアウトファイル（オプション）
│   └── post.html
├── _includes/           # ← 部分テンプレート（オプション）
├── assets/              # ← CSS/JS/画像（オプション）
│   └── css/
│       └── style.scss
├── index.md             # ← トップページ
├── README.md            # ← リポジトリ説明
└── Gemfile              # ← Ruby依存関係（オプション）
```

### 📄 トップページ（`index.md`）の作成

```markdown
---
layout: home
title: "お悔やみ情報"
---

# 山梨日日新聞 お悔やみ情報

このサイトでは、山梨日日新聞から取得したお悔やみ情報を整理して掲載しています。

## 最新情報

下記の投稿一覧から最新のお悔やみ情報をご確認ください。

## 注意事項

- 情報は山梨日日新聞から自動取得しています
- 詳細については各投稿をご確認ください
- お悔やみ申し上げます
```

### 💎 Gemfile（ローカル開発用・オプション）

```ruby
source "https://rubygems.org"

gem "github-pages", group: :jekyll_plugins
gem "jekyll-feed"
gem "jekyll-sitemap"
gem "jekyll-seo-tag"

# Windows用
gem "wdm", "~> 0.1.0" if Gem.win_platform?
```

### 🚀 GitHub Pagesの有効化手順

1. **GitHubでリポジトリを作成**
   ```
   リポジトリ名例: okuyami-info
   Public または Private（Proアカウント必要）
   ```

2. **GitHub Pagesを有効化**
   - リポジトリの Settings タブを開く
   - 左メニューから "Pages" を選択
   - Source: "Deploy from a branch"
   - Branch: "main" または "gh-pages"
   - Folder: "/ (root)" または "/docs"
   - Save をクリック

3. **ローカルにクローン**
   ```bash
   git clone https://github.com/your-username/okuyami-info.git
   cd okuyami-info
   ```

4. **必要ファイルの作成**
   ```bash
   # 設定ファイル作成
   echo "上記の_config.ymlの内容" > _config.yml
   
   # 投稿ディレクトリ作成
   mkdir _posts
   
   # トップページ作成
   echo "上記のindex.mdの内容" > index.md
   
   # 初回コミット
   git add .
   git commit -m "Initial Jekyll setup"
   git push origin main
   ```

5. **サイトURL確認**
   ```
   https://your-username.github.io/okuyami-info
   ```

### 🔧 カスタマイズオプション

#### テーマ変更
```yaml
# _config.yml内で
theme: jekyll-theme-slate        # GitHub Pages標準テーマ
# または
remote_theme: pages-themes/slate # リモートテーマ
```

#### 利用可能なGitHub Pages標準テーマ
- `minima` (デフォルト)
- `jekyll-theme-architect`
- `jekyll-theme-cayman`
- `jekyll-theme-dinky`
- `jekyll-theme-hacker`
- `jekyll-theme-leap-day`
- `jekyll-theme-merlot`
- `jekyll-theme-midnight`
- `jekyll-theme-minimal`
- `jekyll-theme-modernist`
- `jekyll-theme-slate`
- `jekyll-theme-tactile`
- `jekyll-theme-time-machine`

2. **Git設定**
   ```bash
   git config --global user.name "Kurigohan"
   git config --global user.email "jun@taxa.jp"
   ```

3. **認証設定**
   - GitHubトークンまたはSSH認証の設定
   - `git push`が認証なしで実行できる状態

## 使用方法

### 1. インタラクティブモード（推奨）

```bash
python upload_to_github_pages.py
```

実行すると以下の項目を対話的に入力します：
- GitHub Pagesリポジトリのローカルパス
- Markdownファイルのパス（省略可能）
- ブランチ名（デフォルト: main）
- コミットメッセージ（省略可能）

### 2. コマンドラインモード

```bash
python upload_to_github_pages.py --repo /path/to/your/github-pages-repo
```

#### オプション

- `--repo`: GitHub Pagesリポジトリのローカルパス（必須）
- `--file`: アップロードするMarkdownファイルのパス（省略時は最新を自動選択）
- `--branch`: アップロード先のブランチ名（デフォルト: main）
- `--message`: コミットメッセージ

#### 使用例

```bash
# 基本的な使用
python upload_to_github_pages.py --repo "%USERPROFILE%\github-pages-repo"

# 特定のファイルを指定
python upload_to_github_pages.py --repo "%USERPROFILE%\github-pages-repo" --file "okuyami_output/okuyami_20250806_parsed_20250806_123456.md"

# ブランチとコミットメッセージを指定
python upload_to_github_pages.py --repo "%USERPROFILE%\github-pages-repo" --branch "gh-pages" --message "お悔やみ情報を更新"
```

## ファイル構造

スクリプトは以下のような構造でファイルを配置します：

```
your-github-pages-repo/
├── _config.yml
├── _posts/
│   └── 2025-08-06-okuyami-info.md  ← アップロードされるファイル
├── index.md
└── ...
```

## Jekyll投稿形式

生成されるMarkdownファイルは以下のフロントマターを持ちます：

```yaml
---
layout: post
title: "お悔やみ情報 (2025年08月06日)"
date: 2025-08-06 14:30:15 +0900
categories: [obituary, news]
tags: [お悔やみ, 訃報, 山梨]
author: "お悔やみ情報bot"
---
```

## トラブルシューティング

### よくある問題

1. **認証エラー**
   ```
   fatal: Authentication failed
   ```
   - GitHubトークンまたはSSH認証を確認
   - `git push`が手動で実行できるか確認

2. **リポジトリが見つからない**
   ```
   エラー: リポジトリディレクトリが見つかりません
   ```
   - パスが正しいか確認
   - Gitリポジトリが初期化されているか確認

3. **コミットする変更がない**
   ```
   コミットする変更がないか、コミットに失敗しました
   ```
   - 同じファイルが既にコミットされている可能性
   - 手動で`git status`を確認

### デバッグ方法

詳細なエラー情報を確認したい場合：

```bash
cd your-github-pages-repo
git status
git log --oneline -5
```

## セキュリティ注意事項

- GitHubトークンは環境変数として設定し、直接コードに含めない
- プライベートリポジトリの場合は適切なアクセス権限を設定
- 自動実行する場合はGitHub Actionsの使用を検討

## ライセンス

このスクリプトはMITライセンスの下で公開されています。
