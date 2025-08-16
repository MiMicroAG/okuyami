#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Pages アップロードスクリプト
お悔やみ情報Markdownファイルを Jekyll _posts へ配置して GitHub へプッシュ
バックフィル用に --date (YYYY-MM-DD) で投稿日付を上書き可能
"""

import os
import sys
import glob
import subprocess
from datetime import datetime
from typing import Optional
from common_utils import build_front_matter, get_jp_date
import argparse


class GitHubPagesUploader:
    def __init__(self, repo_path: str, branch: str = "main"):
        self.repo_path = repo_path
        self.branch = branch
        self.posts_dir = os.path.join(repo_path, "_posts")

    # 表示用パス短縮
    def _display_path(self, path: str) -> str:
        try:
            p_norm = os.path.normcase(os.path.normpath(path))
            for env_key in ("OneDrive", "USERPROFILE"):
                base = os.environ.get(env_key)
                if not base:
                    continue
                b_norm = os.path.normcase(os.path.normpath(base))
                if p_norm.startswith(b_norm):
                    rest = path[len(base):].lstrip('\\/')
                    return f"%{env_key}%\\{rest}" if rest else f"%{env_key}%"
        except Exception:
            pass
        return path

    def setup_repository(self) -> bool:
        try:
            if not os.path.exists(self.repo_path):
                print(f"エラー: リポジトリが存在しません: {self._display_path(self.repo_path)}")
                return False
            if not os.path.exists(os.path.join(self.repo_path, ".git")):
                print(f"エラー: Gitリポジトリではありません: {self._display_path(self.repo_path)}")
                return False
            os.makedirs(self.posts_dir, exist_ok=True)
            print(f"リポジトリ: {self._display_path(self.repo_path)}")
            print(f"_posts : {self._display_path(self.posts_dir)}")
            return True
        except Exception as e:
            print(f"リポジトリ設定エラー: {e}")
            return False

    def find_latest_markdown_file(self, source_dir: str = "./okuyami_output") -> Optional[str]:
        try:
            md_files = glob.glob(os.path.join(source_dir, "*.md"))
            if not md_files:
                print(f"Markdownが見つかりません: {source_dir}")
                return None
            latest = max(md_files, key=os.path.getctime)
            print(f"最新Markdown: {latest}")
            return latest
        except Exception as e:
            print(f"検索エラー: {e}")
            return None

    def prepare_jekyll_post(self, source_file: str, dt: datetime) -> Optional[str]:
        """既存Markdownを Jekyll post 形式に変換"""
        try:
            date_str = dt.strftime('%Y-%m-%d')
            dest_path = os.path.join(self.posts_dir, f"{date_str}-okuyami-info.md")

            with open(source_file, 'r', encoding='utf-8') as rf:
                content = rf.read()

            # 既存 front matter 除去
            if content.startswith('---'):
                end_pos = content.find('\n---', 3)
                if end_pos != -1:
                    content_rest = content[end_pos + 4:].lstrip('\n')
                else:
                    content_rest = content
            else:
                content_rest = content

            # 見出し日付置換（1回のみ）
            jp_date = dt.strftime('%Y年%m月%d日')
            import re as _re
            content_rest = _re.sub(r'^#\s*お悔やみ情報 \([^)]*\)', f'# お悔やみ情報 ({jp_date})', content_rest, count=1, flags=_re.MULTILINE)

            front = build_front_matter(f'お悔やみ情報 ({get_jp_date(dt)})', dt)

            with open(dest_path, 'w', encoding='utf-8') as wf:
                wf.write(front + content_rest)
            print(f"Jekyll投稿ファイル生成: {self._display_path(dest_path)}")
            return dest_path
        except Exception as e:
            print(f"Jekyll準備エラー: {e}")
            return None

    def run_git_command(self, cmd: list) -> bool:
        try:
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                out = result.stdout.strip()
                if out:
                    print(out)
                return True
            else:
                err = result.stderr.strip()
                if err:
                    print(f"Gitエラー: {err}")
                return False
        except Exception as e:
            print(f"Git実行例外: {e}")
            return False

    def commit_and_push(self, file_path: str, commit_message: Optional[str]) -> bool:
        if commit_message is None:
            commit_message = f"お悔やみ情報を更新 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        rel = os.path.relpath(file_path, self.repo_path)
        print("git add/commit/push 開始")
        # git add
        if not self.run_git_command(['git', 'add', rel]):
            return False
        # 差分有無チェック (ステージ済み比較)。差分なければコミット/プッシュをスキップ
        try:
            diff_check = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', rel], cwd=self.repo_path)
            if diff_check.returncode == 0:
                print("変更なし: コミット/プッシュをスキップします")
                return True
        except Exception as e:
            print(f"差分チェック失敗(継続): {e}")
        # commit
        if not self.run_git_command(['git', 'commit', '-m', commit_message]):
            print("コミット失敗 (内容なしの可能性)")
            return False
        # push
        if not self.run_git_command(['git', 'push', 'origin', self.branch]):
            return False
        print("GitHub Pages へプッシュ完了")
        return True

    def prepare_empty_post(self, dt: datetime, reason: str) -> Optional[str]:
        """休刊日/データ無し用の簡易ポスト生成"""
        try:
            date_str = dt.strftime('%Y-%m-%d')
            dest_path = os.path.join(self.posts_dir, f"{date_str}-okuyami-info.md")
            if os.path.exists(dest_path):
                print(f"警告: 既にポストが存在します: {dest_path} 上書きします")
            jp_date = dt.strftime('%Y年%m月%d日')
            if reason == 'holiday':
                body_msg = '本日は新聞休刊日のため掲載はありません。'
                title_suffix = ' 休刊日'
            else:
                body_msg = '本日のお悔やみ情報はありません。'
                title_suffix = '（掲載なし）'
            from datetime import datetime as _dt
            front = build_front_matter(f'お悔やみ情報 ({jp_date}{title_suffix})', _dt(dt.year, dt.month, dt.day, 0, 0, 0))
            content = (
                f'# お悔やみ情報 ({jp_date})\n\n'
                f'> {body_msg}\n\n'
                '*自動生成: 休刊日/掲載なし判定*\n'
            )
            with open(dest_path, 'w', encoding='utf-8') as wf:
                wf.write(front + content)
            print(f"空ポスト生成: {self._display_path(dest_path)}")
            return dest_path
        except Exception as e:
            print(f"空ポスト生成エラー: {e}")
            return None

    def upload_markdown_file(self, source_file: Optional[str], commit_message: Optional[str], dt: datetime, generate_empty: bool = False, reason: str = 'holiday') -> bool:
        try:
            if not self.setup_repository():
                return False
            if generate_empty:
                jekyll_file = self.prepare_empty_post(dt, reason)
            else:
                if source_file is None:
                    source_file = self.find_latest_markdown_file()
                    if source_file is None:
                        return False
                if not os.path.exists(source_file):
                    print(f"エラー: ファイル未存在: {source_file}")
                    return False
                jekyll_file = self.prepare_jekyll_post(source_file, dt)
            if not jekyll_file:
                return False
            if self.commit_and_push(jekyll_file, commit_message):
                print("\n" + "=" * 50)
                print("アップロード完了")
                print(f"投稿: {os.path.basename(jekyll_file)}")
                print("数分後にサイトへ反映されます")
                print("=" * 50)
                return True
            return False
        except Exception as e:
            print(f"アップロードエラー: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="お悔やみ情報 GitHub Pages アップローダー")
    parser.add_argument('--repo', required=True, help='GitHub Pages リポジトリ (例: ./okuyami-info)')
    parser.add_argument('--file', help='アップロードするMarkdown (未指定で最新)')
    parser.add_argument('--branch', default='main', help='ブランチ (default: main)')
    parser.add_argument('--message', help='コミットメッセージ')
    parser.add_argument('--date', help='投稿日付 YYYY-MM-DD (バックフィル用)')
    parser.add_argument('--infer-date', action='store_true', help='ファイル名(okuyami_YYYYMMDD_)から日付推定')
    parser.add_argument('--generate-empty', action='store_true', help='休刊日/掲載なしの空ポストを生成')
    parser.add_argument('--reason', choices=['holiday', 'nodata'], default='holiday', help='空ポスト理由')
    args = parser.parse_args()

    # 日付決定ロジック
    dt: datetime
    if args.date:
        try:
            dt = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print('エラー: --date は YYYY-MM-DD 形式')
            sys.exit(1)
    elif args.infer_date and args.file:
        import re as _re
        m = _re.search(r'(20\d{6})', os.path.basename(args.file))
        if m:
            try:
                dt = datetime.strptime(m.group(1), '%Y%m%d')
            except ValueError:
                dt = datetime.now()
                print('警告: ファイル名日付解析失敗・現在日時使用')
        else:
            print('警告: ファイル名から日付抽出できず現在日時を使用')
            dt = datetime.now()
    else:
        dt = datetime.now()

    uploader = GitHubPagesUploader(args.repo, args.branch)
    # Force UTF-8 environment to reduce mojibake risk on Windows git
    try:
        os.environ.setdefault('LANG', 'ja_JP.UTF-8')
        os.environ.setdefault('LC_ALL', 'ja_JP.UTF-8')
    except Exception:
        pass
    ok = uploader.upload_markdown_file(
        source_file=args.file,
        commit_message=args.message,
        dt=dt,
        generate_empty=args.generate_empty,
        reason=args.reason
    )
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
