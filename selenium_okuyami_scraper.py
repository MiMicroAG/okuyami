#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山梨日日新聞お悔やみ情報取得スクリプト（Selenium版・修正版）
Microsoft Edge（Chromium）とSeleniumを使用してブラウザ自動化によるログイン認証を行い、
お悔やみ情報を取得してローカルフォルダにテキストファイルとして保存
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import time
import tempfile
import uuid
from datetime import datetime
import re
import shutil
import logging
from typing import Optional, cast

class SeleniumOkuyamiScraper:
    def __init__(self, email, password, output_dir="./okuyami_data", headless=True):
        """
        初期化
        
        Args:
            email (str): ログイン用メールアドレス
            password (str): ログイン用パスワード
            output_dir (str): 出力ディレクトリ
            headless (bool): ヘッドレスモードで実行するか
        """
        self.email = email
        self.password = password
        self.output_dir = output_dir
        self.headless = headless
        self.driver = None
        self.wait = None
        self._temp_user_data_dir = None
        # ログ（必要に応じてINFOに変更可）
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
        self.logger = logging.getLogger(__name__)

        # 出力ディレクトリを作成
        os.makedirs(self.output_dir, exist_ok=True)
    
    def setup_driver(self):
        """
        WebDriverを設定
        """
        try:
            print("ブラウザを起動中...")

            # 既存ドライバの掃除
            self._cleanup_existing_drivers()

            # 一意のユーザーデータディレクトリ
            self._temp_user_data_dir = tempfile.mkdtemp(prefix=f'edge_ud_{uuid.uuid4().hex[:8]}_')

            # 共通オプション
            def apply_common_options(opts):
                if self.headless:
                    opts.add_argument('--headless=new')
                opts.add_argument('--no-sandbox')
                opts.add_argument('--disable-dev-shm-usage')
                opts.add_argument('--disable-gpu')
                opts.add_argument('--window-size=1920,1080')
                opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
                opts.add_argument(f'--user-data-dir={self._temp_user_data_dir}')
                opts.add_argument('--disable-extensions')
                opts.add_argument('--no-first-run')
                opts.add_argument('--disable-default-apps')
                # 画像読み込み無効化（高速化）
                try:
                    opts.add_experimental_option('prefs', {"profile.managed_default_content_settings.images": 2})
                except Exception:
                    pass
                # 速度優先
                try:
                    opts.page_load_strategy = 'eager'
                except Exception:
                    pass

            # Chromeのみ使用（Selenium Managerで自動解決）
            coptions = ChromeOptions()
            apply_common_options(coptions)
            csvc = ChromeService()
            self.driver = webdriver.Chrome(service=csvc, options=coptions)
            self.wait = WebDriverWait(self.driver, 15)
            print("Chrome WebDriverを起動")

            print("ブラウザ起動完了")
            return True
            
        except Exception as e:
            print(f"ブラウザ起動エラー: {e}")
            # ユーザーデータディレクトリの掃除
            self._cleanup_user_data_dir()
            return False
    
    def _get_random_port(self):
        """
        ランダムなポート番号を生成
        """
        import random
        return random.randint(9000, 9999)
    
    def _cleanup_existing_drivers(self):
        """既存のchromedriverプロセスをクリーンアップ"""
        try:
            import subprocess
            # Windowsでchromedriverプロセスを確認・終了
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq chromedriver.exe'],
                capture_output=True, text=True, shell=True
            )
            
            if 'chromedriver.exe' in result.stdout:
                print("既存のchromedriverプロセスを終了中...")
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                             capture_output=True, shell=True)
                time.sleep(2)
        except Exception as e:
            print(f"プロセスクリーンアップエラー: {e}")
    
    def _force_cleanup_drivers(self):
        """
        強制的にchromedriverプロセスをクリーンアップ
        """
        try:
            import subprocess
            try:
                import psutil  # type: ignore
            except ImportError:
                psutil = None  # 選択的依存関係
            
            print("chromedriverプロセスを強制終了中...")
            
            # PSUTILを使用してより確実にプロセスを終了
            if psutil is not None:
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] and 'chromedriver' in proc.info['name'].lower():
                        print(f"プロセス終了: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=3)
            else:
                # psutilがない場合は従来の方法（chromedriver のみ終了）
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                             capture_output=True, shell=True)
            
            # 既存のChrome本体は基本終了しない。必要な場合のみ環境変数で許可
            if os.getenv('OKUYAMI_FORCE_KILL_CHROME', '').strip() == '1':
                try:
                    print('OKUYAMI_FORCE_KILL_CHROME=1 により chrome.exe を終了します')
                    if psutil is not None:
                        for proc in psutil.process_iter(['pid', 'name']):
                            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                                print(f"プロセス終了: {proc.info['name']} (PID: {proc.info['pid']})")
                                proc.terminate()
                                proc.wait(timeout=3)
                    else:
                        subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True, shell=True)
                except Exception as _e:
                    print(f"chrome.exe 終了で例外: {_e}")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"強制クリーンアップエラー: {e}")
            # フォールバック
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                             capture_output=True, shell=True)
                # chrome.exe はフォールバックでも終了しない（環境変数での許可時のみ別途）
                time.sleep(3)
            except:
                pass
    
    def _cleanup_user_data_dir(self):
        """一時ユーザーデータディレクトリを削除"""
        try:
            if self._temp_user_data_dir and os.path.exists(self._temp_user_data_dir):
                shutil.rmtree(self._temp_user_data_dir, ignore_errors=True)
        except Exception as e:
            self.logger.warning(f"ユーザーデータ削除失敗: {e}")
        finally:
            self._temp_user_data_dir = None

    def login(self):
        """
        山梨日日新聞サイトにログイン
        
        Returns:
            bool: ログイン成功時True
        """
        try:
            print("ログイン処理を開始...")
            
            # driver, wait の確認
            if self.driver is None or self.wait is None:
                raise RuntimeError("WebDriver not initialized. Call setup_driver() first.")
            driver = cast(webdriver.Chrome, self.driver)
            wait = cast(WebDriverWait, self.wait)

            # お悔やみページにアクセス
            driver.get("https://www.sannichi.co.jp/news/okuyami")
            time.sleep(3)
            
            # ログインボタンを探してクリック
            try:
                login_button = wait.until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "ログイン"))
                )
                login_button.click()
                print("ログインページに移動")
                time.sleep(3)
            except TimeoutException:
                print("ログインボタンが見つかりません")
                return False
            
            # メールアドレス入力フィールドを探して入力
            try:
                # 複数の方法でメールアドレスフィールドを探す
                email_field = None
                
                # 方法1: type="email"
                try:
                    email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                except NoSuchElementException:
                    pass
                
                # 方法2: name属性にemailを含む
                if not email_field:
                    try:
                        email_field = driver.find_element(By.CSS_SELECTOR, "input[name*='email']")
                    except NoSuchElementException:
                        pass
                
                # 方法3: name属性にmailを含む
                if not email_field:
                    try:
                        email_field = driver.find_element(By.CSS_SELECTOR, "input[name*='mail']")
                    except NoSuchElementException:
                        pass
                
                # 方法4: id属性にemailを含む
                if not email_field:
                    try:
                        email_field = driver.find_element(By.CSS_SELECTOR, "input[id*='email']")
                    except NoSuchElementException:
                        pass
                
                if email_field:
                    email_field.clear()
                    email_field.send_keys(self.email)
                    print("メールアドレスを入力")
                    time.sleep(1)
                else:
                    print("メールアドレス入力フィールドが見つかりません")
                    return False
                    
            except Exception as e:
                print(f"メールアドレス入力エラー: {e}")
                return False
            
            # パスワード入力フィールドを探して入力
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                password_field.clear()
                password_field.send_keys(self.password)
                print("パスワードを入力")
                time.sleep(1)
            except NoSuchElementException:
                print("パスワード入力フィールドが見つかりません")
                return False
            
            # ログインボタンをクリック
            try:
                # 複数の方法でログインボタンを探す
                submit_button = None
                
                # 方法1: type="submit"
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                except NoSuchElementException:
                    pass
                
                # 方法2: input[type="submit"]
                if not submit_button:
                    try:
                        submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                    except NoSuchElementException:
                        pass
                
                # 方法3: ログインテキストを含むボタン
                if not submit_button:
                    try:
                        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'ログイン')]")
                    except NoSuchElementException:
                        pass
                
                # 方法4: 送信テキストを含むボタン
                if not submit_button:
                    try:
                        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), '送信')]")
                    except NoSuchElementException:
                        pass
                
                if submit_button:
                    submit_button.click()
                    print("ログインボタンをクリック")
                    time.sleep(5)
                else:
                    print("ログイン送信ボタンが見つかりません")
                    return False
                    
            except Exception as e:
                print(f"ログインボタンクリックエラー: {e}")
                return False
            
            # ログイン成功の確認
            try:
                # ログアウトボタンまたはユーザー情報の存在を確認
                logout_found = False
                
                # 複数の方法でログアウト要素を探す
                try:
                    driver.find_element(By.LINK_TEXT, "ログアウト")
                    logout_found = True
                except NoSuchElementException:
                    pass
                
                if not logout_found:
                    try:
                        driver.find_element(By.PARTIAL_LINK_TEXT, "ログアウト")
                        logout_found = True
                    except NoSuchElementException:
                        pass
                
                if not logout_found:
                    try:
                        driver.find_element(By.CSS_SELECTOR, "a[href*='logout']")
                        logout_found = True
                    except NoSuchElementException:
                        pass
                
                if logout_found:
                    print("ログイン成功")
                    return True
                else:
                    print("ログイン失敗 - ログアウトボタンが見つかりません")
                    # デバッグ用に現在のページタイトルとURLを表示
                    print(f"現在のページ: {driver.title}")
                    print(f"現在のURL: {driver.current_url}")
                    return False
                    
            except Exception as e:
                print(f"ログイン確認エラー: {e}")
                return False
                
        except Exception as e:
            print(f"ログインエラー: {e}")
            return False
    
    def get_okuyami_list(self):
        """
        お悔やみ情報一覧を取得
        
        Returns:
            list: お悔やみ情報のリスト（日付、タイトル、URL）
        """
        try:
            print("お悔やみ一覧を取得中...")
            
            if self.driver is None:
                raise RuntimeError("WebDriver not initialized.")
            driver = cast(webdriver.Chrome, self.driver)
            # お悔やみページに移動
            driver.get("https://www.sannichi.co.jp/news/okuyami")
            time.sleep(3)
            
            okuyami_list = []
            
            # お悔やみリンクを抽出
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    
                    # お悔やみ記事のリンクを判定
                    if text.startswith('おくやみ（') and '日付）' in text and href:
                        okuyami_list.append({
                            'title': text,
                            'url': href,
                            'date': self._extract_date_from_title(text)
                        })
                except Exception:
                    continue
            
            print(f"お悔やみ情報 {len(okuyami_list)} 件を発見")
            return okuyami_list
            
        except Exception as e:
            print(f"一覧取得エラー: {e}")
            return []
    
    def _extract_date_from_title(self, title):
        """
        タイトルから日付を抽出
        
        Args:
            title (str): タイトル文字列
            
        Returns:
            str: 抽出された日付（YYYY-MM-DD形式）
        """
        # 「おくやみ（８月４日付）」のような形式から日付を抽出
        match = re.search(r'（(\d+)月(\d+)日付）', title)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            
            # 年は現在年を使用
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            if month > current_month:
                year = current_year - 1
            else:
                year = current_year
            
            return f"{year:04d}-{month:02d}-{day:02d}"
        
        return "unknown"
    
    def get_okuyami_content(self, url):
        """
        指定URLのお悔やみ情報を取得
        
        Args:
            url (str): お悔やみ記事のURL
            
        Returns:
            str: お悔やみ情報のテキスト
        """
        try:
            print(f"お悔やみ情報を取得中: {url}")
            
            if self.driver is None:
                raise RuntimeError("WebDriver not initialized.")
            driver = cast(webdriver.Chrome, self.driver)
            driver.get(url)
            time.sleep(3)
            
            # お悔やみ情報の本文部分を抽出
            okuyami_content = self._extract_okuyami_content()
            
            # 空の場合はエラーメッセージ
            if not okuyami_content.strip():
                okuyami_content = "お悔やみ情報を取得できませんでした"
            
            return okuyami_content
            
        except Exception as e:
            print(f"コンテンツ取得エラー: {e}")
            return f"エラー: {e}"
    
    def _extract_okuyami_content(self):
        """
        ページからお悔やみ情報のみを抽出
        
        Returns:
            str: 抽出されたお悔やみ情報
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            if self.driver is None or self.wait is None:
                raise RuntimeError("WebDriver not initialized.")
            driver = cast(webdriver.Chrome, self.driver)
            wait = cast(WebDriverWait, self.wait)
            
            # 方法1: #p_textarea要素から直接取得（参考コードと同じ方法）
            try:
                # #p_textarea要素が存在するまで待機
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#p_textarea")))
                textarea_element = driver.find_element(By.CSS_SELECTOR, "#p_textarea")
                content = textarea_element.text
                # --- Normalization & cleanup to mitigate console mojibake ---
                try:
                    import unicodedata, re as _re
                    # NFC normalize
                    content_norm = unicodedata.normalize('NFC', content)
                    # Remove isolated surrogate / non-BMP control-like chars except line breaks & Japanese common range
                    content_norm = ''.join(c for c in content_norm if (c >= ' ' and c != '\uFFFD'))
                    # Collapse any repeating replacement markers
                    content = _re.sub(r'\uFFFD+', '�', content_norm)
                except Exception:
                    pass
                if content and content.strip():
                    # ログ出力時の文字化け片(� や ���)を除去し統一
                    try:
                        import re as _relog
                        log_msg = "お悔やみ情報を#p_textareaから取得しました"
                        log_msg = _relog.sub(r'�+', '�', log_msg)  # 連続した�を1つへ
                        log_msg = log_msg.replace('�', '')  # 最終的に除去（表示簡潔化）
                        print(log_msg)
                    except Exception:
                        print("お悔やみ情報を#p_textareaから取得しました")
                    return self._filter_okuyami_text(content)
            except Exception as e:
                print(f"#p_textarea要素の取得に失敗: {e}")
            
            # 方法2: 記事本文のセレクタを試す
            article_selectors = [
                "article",
                ".article-body",
                ".news-body", 
                ".content-body",
                "#main-content",
                ".main-content",
                ".article-content",
                "#article",
                ".post-content"
            ]
            
            for selector in article_selectors:
                try:
                    article_element = driver.find_element(By.CSS_SELECTOR, selector)
                    content = article_element.text
                    if content and content.strip():
                        print(f"お悔やみ情報を{selector}から取得しました")
                        return self._filter_okuyami_text(content)
                except:
                    continue
            
            # 方法3: ページ全体から抽出（最後の手段）
            print("記事要素が見つからないため、ページ全体から抽出します")
            body_text = driver.find_element(By.TAG_NAME, "body").text
            return self._filter_okuyami_text(body_text)
            
        except Exception as e:
            print(f"お悔やみ情報抽出エラー: {e}")
            return ""
    
    def _filter_okuyami_text(self, text):
        """
        テキストからお悔やみ情報のみをフィルタリング（簡素化版）
        
        Args:
            text (str): 元のテキスト
            
        Returns:
            str: フィルタリングされたお悔やみ情報
        """
        # #p_textareaから取得した場合は、既にお悔やみ情報のみの可能性が高い
        # 簡単なクリーニングのみ実行
        
        lines = text.split('\n')
        filtered_lines = []
        
        # 明らかに不要な行のみをスキップ
        skip_patterns = [
            r'^音声読み上げ$',
            r'^写真画像を拡大する$',
            r'^斎場の地図はこちら$',
            r'^Copyright.*$',
            r'^〒\d{3}-\d{4}.*$',
            r'^\(055\).*$',
            r'^山梨日日新聞社$',
            r'^ホーム$',
            r'^ログアウト$',
            r'^記事スクラップ$',
            r'^マイニュースメール$'
        ]
        
        for line in lines:
            line = line.strip()
            
            # 空行をスキップ
            if not line:
                continue
            
            # 明らかに不要な行をスキップ
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line):
                    should_skip = True
                    break
            
            if not should_skip:
                filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines)
        
        # 結果が短すぎる場合は元のテキストを返す
        if len(result.strip()) < 100:
            print("フィルタリング後のテキストが短すぎるため、元のテキストを使用します")
            return text
        
        return result
    
    def save_to_file(self, content, date, title):
        """
        コンテンツをファイルに保存
        
        Args:
            content (str): 保存するコンテンツ
            date (str): 日付
            title (str): タイトル
        """
        try:
            # ファイル名を生成（日付ベース）
            safe_date = date.replace('-', '')
            filename = f"okuyami_{safe_date}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            # ファイルに保存
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"タイトル: {title}\n")
                f.write(f"日付: {date}\n")
                f.write("=" * 50 + "\n\n")
                f.write(content)
            
            print(f"ファイル保存完了: {filepath}")
            
        except Exception as e:
            print(f"ファイル保存エラー: {e}")
    
    def scrape_by_date(self, target_date):
        """
        指定日のお悔やみ情報を取得
        
        Args:
            target_date (str): 対象日付（YYYY-MM-DD形式）
            
        Returns:
            bool: 成功時True
        """
        if not self.setup_driver():
            return False
        
        try:
            if not self.login():
                return False
            
            # お悔やみ一覧を取得
            okuyami_list = self.get_okuyami_list()
            
            # 指定日の情報を検索
            target_item = None
            for item in okuyami_list:
                if item['date'] == target_date:
                    target_item = item
                    break
            
            if not target_item:
                print(f"指定日（{target_date}）のお悔やみ情報が見つかりませんでした")
                print("利用可能な日付:")
                for item in okuyami_list[:10]:  # 最新10件を表示
                    print(f"  - {item['date']}: {item['title']}")
                return False
            
            # コンテンツを取得
            content = self.get_okuyami_content(target_item['url'])
            
            # ファイルに保存
            self.save_to_file(content, target_date, target_item['title'])
            
            print(f"お悔やみ情報の取得が完了しました: {target_date}")
            return True
            
        except Exception as e:
            print(f"スクレイピングエラー: {e}")
            return False
        finally:
            self.cleanup()
    
    def scrape_latest(self, count=1):
        """
        最新のお悔やみ情報を取得
        
        Args:
            count (int): 取得する件数
            
        Returns:
            bool: 成功時True
        """
        if not self.setup_driver():
            return False
        
        try:
            if not self.login():
                return False
            
            # お悔やみ一覧を取得
            okuyami_list = self.get_okuyami_list()
            
            if not okuyami_list:
                print("お悔やみ情報が見つかりませんでした")
                return False
            
            print(f"最新{count}件のお悔やみ情報を取得します...")
            
            success_count = 0
            # 最新の件数分を処理
            for i, item in enumerate(okuyami_list[:count]):
                print(f"\n処理中 ({i+1}/{count}): {item['title']}")
                
                try:
                    # コンテンツを取得
                    content = self.get_okuyami_content(item['url'])
                    
                    # ファイルに保存
                    self.save_to_file(content, item['date'], item['title'])
                    success_count += 1
                    
                    # 次のリクエストまで少し待機
                    if i < count - 1:
                        time.sleep(3)
                        
                except Exception as e:
                    print(f"取得エラー ({item['date']}): {e}")
                    continue
            
            print(f"\nお悔やみ情報の取得が完了しました: {success_count}/{count}件成功")
            return success_count > 0
            
        except Exception as e:
            print(f"スクレイピングエラー: {e}")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        リソースのクリーンアップ
        """
        if self.driver:
            print("ブラウザを終了中...")
            try:
                self.driver.quit()
            except Exception as e:
                print(f"ブラウザ終了エラー: {e}")
            finally:
                self.driver = None
        # ユーザーデータディレクトリも削除
        self._cleanup_user_data_dir()


def main():
    """
    メイン関数
    """
    import sys
    import argparse
    
    # 設定（環境変数・config.ini対応）
    import configparser
    OUTPUT_DIR = "./okuyami_data"
    HEADLESS = True  # ヘッドレスモード（Falseにするとブラウザが表示される）
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="山梨日日新聞お悔やみ情報取得スクリプト（Selenium版）")
    parser.add_argument('--auto', action='store_true', help='自動モード（最新1件取得）')
    parser.add_argument('--date', type=str, help='指定日のお悔やみ情報を取得 (YYYY-MM-DD)')
    parser.add_argument('--count', type=int, default=1, help='取得件数（デフォルト: 1）')
    parser.add_argument('--headless', action='store_true', default=True, help='ヘッドレスモード')
    parser.add_argument('--no-headless', action='store_true', help='ブラウザ表示モード')
    parser.add_argument('--email', type=str, help='ログインメールアドレス（環境変数OKUYAMI_EMAIL優先）')
    parser.add_argument('--password', type=str, help='ログインパスワード（環境変数OKUYAMI_PASSWORD優先）')
    parser.add_argument('--prefer-today', action='store_true', help='本日分がある場合のみ取得（なければ中止）')
    
    # 引数がない場合はインタラクティブモード
    if len(sys.argv) == 1:
        print("山梨日日新聞お悔やみ情報取得スクリプト（Selenium版）")
        print("=" * 50)
        
        while True:
            print("\n選択してください:")
            print("1. 指定日のお悔やみ情報を取得")
            print("2. 最新のお悔やみ情報を取得")
            print("3. 最新5件のお悔やみ情報を取得")
            print("4. ブラウザ表示モードで実行（デバッグ用）")
            print("0. 終了")
            
            choice = input("\n選択 (0-4): ").strip()
            
            if choice == "0":
                print("終了します")
                break
            elif choice == "1":
                date_str = input("日付を入力してください (YYYY-MM-DD): ").strip()
                try:
                    # 日付形式の検証
                    datetime.strptime(date_str, '%Y-%m-%d')
                    # 認証情報の取得
                    cfg_email, cfg_password = None, None
                    config = configparser.ConfigParser()
                    if os.path.exists('config.ini'):
                        config.read('config.ini', encoding='utf-8')
                        cfg_email = config.get('auth', 'email', fallback=None)
                        cfg_password = config.get('auth', 'password', fallback=None)
                    email = os.getenv('OKUYAMI_EMAIL', cfg_email)
                    password = os.getenv('OKUYAMI_PASSWORD', cfg_password)
                    if not email or not password:
                        print('認証情報が見つかりません。環境変数OKUYAMI_EMAIL/OKUYAMI_PASSWORD、またはconfig.iniを設定してください。')
                        sys.exit(1)
                    scraper = SeleniumOkuyamiScraper(email, password, OUTPUT_DIR, HEADLESS)
                    success = scraper.scrape_by_date(date_str)
                    sys.exit(0 if success else 1)
                except ValueError:
                    print("日付形式が正しくありません (YYYY-MM-DD)")
            elif choice == "2":
                config = configparser.ConfigParser()
                cfg_email, cfg_password = None, None
                if os.path.exists('config.ini'):
                    config.read('config.ini', encoding='utf-8')
                    cfg_email = config.get('auth', 'email', fallback=None)
                    cfg_password = config.get('auth', 'password', fallback=None)
                email = os.getenv('OKUYAMI_EMAIL', cfg_email)
                password = os.getenv('OKUYAMI_PASSWORD', cfg_password)
                if not email or not password:
                    print('認証情報が見つかりません。環境変数OKUYAMI_EMAIL/OKUYAMI_PASSWORD、またはconfig.iniを設定してください。')
                    sys.exit(1)
                scraper = SeleniumOkuyamiScraper(email, password, OUTPUT_DIR, HEADLESS)
                success = scraper.scrape_latest(1)
                sys.exit(0 if success else 1)
            elif choice == "3":
                config = configparser.ConfigParser()
                cfg_email, cfg_password = None, None
                if os.path.exists('config.ini'):
                    config.read('config.ini', encoding='utf-8')
                    cfg_email = config.get('auth', 'email', fallback=None)
                    cfg_password = config.get('auth', 'password', fallback=None)
                email = os.getenv('OKUYAMI_EMAIL', cfg_email)
                password = os.getenv('OKUYAMI_PASSWORD', cfg_password)
                if not email or not password:
                    print('認証情報が見つかりません。環境変数OKUYAMI_EMAIL/OKUYAMI_PASSWORD、またはconfig.iniを設定してください。')
                    sys.exit(1)
                scraper = SeleniumOkuyamiScraper(email, password, OUTPUT_DIR, HEADLESS)
                success = scraper.scrape_latest(5)
                sys.exit(0 if success else 1)
            elif choice == "4":
                print("ブラウザ表示モードで最新1件を取得します...")
                config = configparser.ConfigParser()
                cfg_email, cfg_password = None, None
                if os.path.exists('config.ini'):
                    config.read('config.ini', encoding='utf-8')
                    cfg_email = config.get('auth', 'email', fallback=None)
                    cfg_password = config.get('auth', 'password', fallback=None)
                email = os.getenv('OKUYAMI_EMAIL', cfg_email)
                password = os.getenv('OKUYAMI_PASSWORD', cfg_password)
                if not email or not password:
                    print('認証情報が見つかりません。環境変数OKUYAMI_EMAIL/OKUYAMI_PASSWORD、またはconfig.iniを設定してください。')
                    sys.exit(1)
                scraper = SeleniumOkuyamiScraper(email, password, OUTPUT_DIR, headless=False)
                success = scraper.scrape_latest(1)
                sys.exit(0 if success else 1)
            else:
                print("無効な選択です")
    else:
        # コマンドライン引数モード
        args = parser.parse_args()
        
        # ヘッドレスモードの設定
        headless_mode = True
        if args.no_headless:
            headless_mode = False
        elif args.headless:
            headless_mode = True
        # 認証情報の決定（引数 > 環境変数 > config.ini）
        config = configparser.ConfigParser()
        cfg_email, cfg_password = None, None
        if os.path.exists('config.ini'):
            config.read('config.ini', encoding='utf-8')
            cfg_email = config.get('auth', 'email', fallback=None)
            cfg_password = config.get('auth', 'password', fallback=None)
        email = args.email or os.getenv('OKUYAMI_EMAIL', cfg_email)
        password = args.password or os.getenv('OKUYAMI_PASSWORD', cfg_password)
        if not email or not password:
            print('認証情報が見つかりません。--email/--password、環境変数OKUYAMI_EMAIL/OKUYAMI_PASSWORD、またはconfig.iniを設定してください。')
            sys.exit(1)

        scraper = SeleniumOkuyamiScraper(email, password, OUTPUT_DIR, headless_mode)
        
        try:
            if args.auto:
                if args.prefer_today:
                    print("自動モード: 本日分がある場合のみ取得...")
                    # 本日分のみ
                    today = datetime.now().strftime('%Y-%m-%d')
                    success = scraper.scrape_by_date(today)
                else:
                    # 自動モード（最新1件取得）
                    print("自動モード: 最新のお悔やみ情報を取得...")
                    success = scraper.scrape_latest(1)
            elif args.date:
                # 指定日取得
                datetime.strptime(args.date, '%Y-%m-%d')  # 日付形式検証
                print(f"指定日のお悔やみ情報を取得: {args.date}")
                success = scraper.scrape_by_date(args.date)
            else:
                # 最新件数指定取得
                print(f"最新{args.count}件のお悔やみ情報を取得...")
                success = scraper.scrape_latest(args.count)
            
            sys.exit(0 if success else 1)
            
        except ValueError:
            print(f"エラー: 日付形式が正しくありません ({args.date})")
            sys.exit(1)
        except Exception as e:
            print(f"実行エラー: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

