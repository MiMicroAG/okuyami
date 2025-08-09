#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pages アップロードスクリプト
お悔やみ情報のMarkdownファイルをGitHub Pagesリポジトリにアップロード
"""

import os
import sys
import subprocess
import shutil
import glob
from datetime import datetime
import argparse

class GitHubPagesUploader:
    def _display_path(self, path: str) -> str:
        """ユーザー名を含む先頭パスを環境変数表記に置換して表示用に整形"""
        try:
            p_norm = os.path.normcase(os.path.normpath(path))
            one = os.environ.get('OneDrive')
            usr = os.environ.get('USERPROFILE')
            if one:
                one_norm = os.path.normcase(os.path.normpath(one))
                if p_norm.startswith(one_norm):
                    rest = path[len(one):].lstrip('\\/')
                    return f"%OneDrive%\\{rest}" if rest else "%OneDrive%"
            if usr:
                usr_norm = os.path.normcase(os.path.normpath(usr))
                if p_norm.startswith(usr_norm):
                    rest = path[len(usr):].lstrip('\\/')
                    return f"%USERPROFILE%\\{rest}" if rest else "%USERPROFILE%"
        except Exception:
            pass
        return path
    def __init__(self, repo_path, branch="main"):
        """
        初期化
        
        Args:
            repo_path (str): GitHub Pagesリポジトリのローカルパス
            branch (str): アップロード対象のブランチ名
        """
        self.repo_path = repo_path
        self.branch = branch
        self.posts_dir = os.path.join(repo_path, "_posts")
        
    def setup_repository(self):
        """
        リポジトリの設定と準備
        """
        try:
            # リポジトリディレクトリの存在確認
            if not os.path.exists(self.repo_path):
                print(f"エラー: リポジトリディレクトリが見つかりません: {self._display_path(self.repo_path)}")
                return False
            
            # _postsディレクトリの作成
            os.makedirs(self.posts_dir, exist_ok=True)
            
            # Gitリポジトリかチェック
            git_dir = os.path.join(self.repo_path, ".git")
            if not os.path.exists(git_dir):
                print(f"エラー: {self._display_path(self.repo_path)} はGitリポジトリではありません")
                return False
            
            print(f"リポジトリパス: {self._display_path(self.repo_path)}")
            print(f"投稿ディレクトリ: {self._display_path(self.posts_dir)}")
            return True
            
        except Exception as e:
            print(f"リポジトリ設定エラー: {e}")
            return False
    
    def find_latest_markdown_file(self, source_dir="./okuyami_output"):
        """
        最新のMarkdownファイルを検索
        
        Args:
            source_dir (str): 検索対象ディレクトリ
            
        Returns:
            str: 最新のMarkdownファイルのパス（見つからない場合はNone）
        """
        try:
            # Markdownファイルのパターン
            pattern = os.path.join(source_dir, "*.md")
            md_files = glob.glob(pattern)
            
            if not md_files:
                print(f"Markdownファイルが見つかりません: {source_dir}")
                return None
            
            # 最新のファイルを取得（作成時刻順）
            latest_file = max(md_files, key=os.path.getctime)
            print(f"最新のMarkdownファイル: {latest_file}")
            return latest_file
            
        except Exception as e:
            print(f"ファイル検索エラー: {e}")
            return None
    
    def prepare_jekyll_post(self, source_file):
        """
        JekyllのPost形式に変換
        
        Args:
            source_file (str): 元のMarkdownファイルパス
            
        Returns:
            str: 変換後のファイルパス
        """
        try:
            # 現在の日付でファイル名を生成
            date_str = datetime.now().strftime("%Y-%m-%d")
            base_name = f"{date_str}-okuyami-info.md"
            dest_file = os.path.join(self.posts_dir, base_name)
            
            # ファイルを読み込み
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Jekyll用のフロントマターを修正
            jekyll_frontmatter = f"""---
layout: post
title: "お悔やみ情報 ({datetime.now().strftime('%Y年%m月%d日')})"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: [obituary, news]
tags: [お悔やみ, 訃報, 山梨]
author: "お悔やみ情報bot"
---

"""
            
            # 既存のフロントマターを削除して新しいものに置換
            if content.startswith('---'):
                # 既存のフロントマターの終了位置を見つける
                end_pos = content.find('---', 3)
                if end_pos != -1:
                    content = content[end_pos + 3:].lstrip('\n')
            
            # 新しいコンテンツを作成
            new_content = jekyll_frontmatter + content
            
            # ファイルに保存
            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"Jekyll投稿ファイルを作成: {self._display_path(dest_file)}")
            return dest_file
            
        except Exception as e:
            print(f"Jekyll投稿準備エラー: {e}")
            return None
    
    def run_git_command(self, command, cwd=None):
        """
        Gitコマンドを実行
        
        Args:
            command (list): 実行するGitコマンド
            cwd (str): 作業ディレクトリ
            
        Returns:
            bool: 成功した場合True
        """
        try:
            if cwd is None:
                cwd = self.repo_path
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                if result.stdout.strip():
                    print(f"Git出力: {result.stdout.strip()}")
                return True
            else:
                print(f"Gitエラー: {result.stderr.strip()}")
                return False
                
        except Exception as e:
            print(f"Gitコマンド実行エラー: {e}")
            return False
    
    def commit_and_push(self, file_path, commit_message=None):
        """
        ファイルをコミットしてプッシュ
        
        Args:
            file_path (str): コミット対象のファイルパス
            commit_message (str): コミットメッセージ
            
        Returns:
            bool: 成功した場合True
        """
        try:
            if commit_message is None:
                commit_message = f"お悔やみ情報を更新 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            
            # 相対パスに変換
            rel_file_path = os.path.relpath(file_path, self.repo_path)
            
            print(f"Gitコミット・プッシュを開始...")
            
            # git add
            if not self.run_git_command(['git', 'add', rel_file_path]):
                return False
            
            # git commit
            if not self.run_git_command(['git', 'commit', '-m', commit_message]):
                print("コミットする変更がないか、コミットに失敗しました")
                return False
            
            # git push
            if not self.run_git_command(['git', 'push', 'origin', self.branch]):
                return False
            
            print(f"GitHub Pagesへのアップロードが完了しました")
            return True
            
        except Exception as e:
            print(f"コミット・プッシュエラー: {e}")
            return False
    
    def upload_markdown_file(self, source_file=None, commit_message=None):
        """
        Markdownファイルをアップロード
        
        Args:
            source_file (str): アップロード対象のMarkdownファイル（Noneの場合は最新を自動検索）
            commit_message (str): コミットメッセージ
            
        Returns:
            bool: 成功した場合True
        """
        try:
            # リポジトリの準備
            if not self.setup_repository():
                return False
            
            # ソースファイルの決定
            if source_file is None:
                source_file = self.find_latest_markdown_file()
                if source_file is None:
                    return False
            
            if not os.path.exists(source_file):
                print(f"エラー: ファイルが見つかりません: {source_file}")
                return False
            
            # Jekyll投稿形式に変換
            jekyll_file = self.prepare_jekyll_post(source_file)
            if jekyll_file is None:
                return False
            
            # GitHub Pagesにアップロード
            success = self.commit_and_push(jekyll_file, commit_message)
            
            if success:
                print("\n" + "="*50)
                print("アップロード完了!")
                print(f"ファイル: {os.path.basename(jekyll_file)}")
                print("GitHub Pagesで数分後に更新が反映されます。")
                print("="*50)
            
            return success
            
        except Exception as e:
            print(f"アップロードエラー: {e}")
            return False


def main():
    """
    メイン関数
    """
    parser = argparse.ArgumentParser(description="GitHub Pages お悔やみ情報アップローダー")
    parser.add_argument("--repo", required=True, help="GitHub Pagesリポジトリのローカルパス")
    parser.add_argument("--file", help="アップロードするMarkdownファイルのパス（省略時は最新を自動選択）")
    parser.add_argument("--branch", default="main", help="アップロード先のブランチ名（デフォルト: main）")
    parser.add_argument("--message", help="コミットメッセージ")
    
    # 引数がない場合はインタラクティブモード
    if len(sys.argv) == 1:
        print("GitHub Pages お悔やみ情報アップローダー")
        print("=" * 40)
        
        # リポジトリパスの入力
        repo_path = input("GitHub Pagesリポジトリのローカルパスを入力してください: ").strip()
        if not repo_path:
            print("リポジトリパスが入力されていません")
            return
        
        # ファイルパスの入力（オプション）
        file_path = input("Markdownファイルのパス（Enterで最新を自動選択）: ").strip()
        if not file_path:
            file_path = None
        
        # ブランチ名の入力
        branch = input("ブランチ名（Enterでmain）: ").strip()
        if not branch:
            branch = "main"
        
        # コミットメッセージの入力
        commit_msg = input("コミットメッセージ（Enterで自動生成）: ").strip()
        if not commit_msg:
            commit_msg = None
        
        # アップロード実行
        uploader = GitHubPagesUploader(repo_path, branch)
        success = uploader.upload_markdown_file(file_path, commit_msg)
        
    else:
        # コマンドライン引数モード
        args = parser.parse_args()
        
        uploader = GitHubPagesUploader(args.repo, args.branch)
        success = uploader.upload_markdown_file(args.file, args.message)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
