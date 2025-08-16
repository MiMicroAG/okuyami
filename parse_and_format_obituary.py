#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
お悔やみ情報解析・整理スクリプト
お悔やみ情報テキストファイルを読み込み、市町村別に表形式で整理してCSVファイルに出力
"""

import re
import csv
import os
from datetime import datetime
import pandas as pd
from common_utils import compute_priority, detect_holiday, get_jp_date, build_front_matter
import configparser
from typing import Optional
try:
    import requests  # optional
except Exception:
    requests = None  # type: ignore

class OkuyamiParser:
    def __init__(self):
        """
        初期化
        """
        self.data = []
        self.current_region = ""
        self.current_city = ""

    def _get_site_url(self) -> str:
        """Jekyllの_config.yml から公開サイトURLを組み立てる。失敗時は既定値。
        優先: 環境変数 OKUYAMI_SITE_URL
        次点: okuyami-info/_config.yml の url + baseurl
        既定: https://MiMicroAG.github.io/okuyami-info
        """
        env_url = os.getenv('OKUYAMI_SITE_URL')
        if env_url and env_url.strip():
            return env_url.strip()
        cfg_path = os.path.join(os.path.dirname(__file__), 'okuyami-info', '_config.yml')
        site = 'https://MiMicroAG.github.io/okuyami-info'
        try:
            if os.path.exists(cfg_path):
                url_val, baseurl_val = '', ''
                import re as _re
                with open(cfg_path, 'r', encoding='utf-8') as yf:
                    for line in yf:
                        m = _re.match(r"\s*url:\s*\"?([^\"\n#]+)\"?", line)
                        if m:
                            url_val = m.group(1).strip()
                        m2 = _re.match(r"\s*baseurl:\s*\"?([^\"\n#]+)\"?", line)
                        if m2:
                            baseurl_val = m2.group(1).strip()
                if url_val:
                    if baseurl_val:
                        if baseurl_val.startswith('/'):
                            site = f"{url_val}{baseurl_val}"
                        else:
                            site = f"{url_val}/{baseurl_val}"
                    else:
                        site = url_val
        except Exception:
            pass
        return site

    def _get_today_post_url(self) -> str:
        """当日の投稿URLを生成（Jekyllのpermalink設定に基づく）"""
        site = self._get_site_url().rstrip('/')
        today = datetime.now()
        # _config.yml の collections.posts.permalink に合わせて /posts/YYYY/MM/DD/okuyami-info/
        return f"{site}/posts/{today.strftime('%Y/%m/%d')}/okuyami-info/"

    def _normalize_municipality(self, name: str) -> str:
        """市町村名の空白（半角/全角）を正規化して除去する。
        例: "甲　府" -> "甲府", "南 アルプス市" -> "南アルプス市"
        """
        if not name:
            return name
        # 全角スペースを削除
        name = name.replace('\u3000', '')
        # 半角スペースやその他の空白を削除
        name = re.sub(r"\s+", "", name)
        return name
    
    def parse_file(self, filepath):
        """
        お悔やみ情報ファイルを解析
        
        Args:
            filepath (str): 入力ファイルのパス
            
        Returns:
            list: 解析されたお悔やみ情報のリスト
        """
        self.data = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # --- 前処理: 1行に詰め込まれているケースに対応するため、区切り記号前に改行を挿入 ---
            # 既に改行の直後にある場合は挿入しない (先読み否定)
            import re as _re_pre
            # Region 区切り '■'
            content = _re_pre.sub(r'(?<!\n)■', '\n■', content)
            # 二つ目の地域終端記号直後に人物が続くケース: "■甲府■姓名さん" → 改行
            content = _re_pre.sub(r'(■[^\n■]{0,30}?■)(?=\S)', r'\1\n', content)
            # 市町村/人物開始 '◇'
            content = _re_pre.sub(r'(?<!\n)◇', '\n◇', content)
            # 句点+スペース無しで直後に新しい人物 (漢字～ さん（) が続く場合は改行
            content = _re_pre.sub(r'。(?!\n)(?=[一-龥々〆〇][^。\n]{0,40}?さん（)', '。\n', content)
            # 連続した改行を1つに圧縮
            content = _re_pre.sub(r'\n{2,}', '\n', content)
            
            # ヘッダー部分をスキップして本文部分を取得
            lines = content.split('\n')
            start_index = 0
            
            # "====" の行を見つけて、その次の行から開始
            for i, line in enumerate(lines):
                if '=' * 10 in line:
                    start_index = i + 1
                    break
            
            # 本文部分を解析
            self._parse_content(lines[start_index:])
            
            return self.data
            
        except Exception as e:
            print(f"ファイル解析エラー: {e}")
            return []
    
    def _parse_content(self, lines):
        """
        お悔やみ情報の本文を解析
        
        Args:
            lines (list): テキストファイルの行リスト
        """
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 空行をスキップ
            if not line:
                i += 1
                continue
            
            # 地域セクションの検出
            region_match = re.match(r'■\s*(.*?)\s*■', line)
            if region_match:
                self.current_region = region_match.group(1).strip()
                self.current_city = ""  # 地域が変わったら市町村をリセット
                i += 1
                continue
            # フォールバック: 誤って "■ 甲　府　" と単独行になり次行が人物開始("■姓名さん(")の場合
            if line.startswith('■') and 'さん（' not in line:
                # 次行確認
                if i + 1 < len(lines):
                    nxt = lines[i+1].lstrip()
                    if nxt.startswith('■') and 'さん（' in nxt:
                        # 現行行を地域名、次行の先頭 '■' は人物行から除去
                        tmp_region = line.lstrip('■').strip()
                        tmp_region = re.sub(r'\s+', ' ', tmp_region)
                        if tmp_region:
                            self.current_region = tmp_region
                            self.current_city = ""
                        # 次行側の先頭 '■' を除去
                        lines[i+1] = re.sub(r'^\s*■', '', lines[i+1])
                        i += 1
                        continue
            
            # 市町村セクションの検出
            if line.startswith('◇'):
                rest = line[1:].strip()
                # 既知市町村（山梨県内想定）の最長一致で先頭を切り出し
                known_munis = [
                    '富士河口湖町', '市川三郷町', '富士吉田市', '山梨市', '大月市', '甲府市', '甲斐市', '中央市',
                    '南アルプス市', '笛吹市', '北杜市', '都留市', '上野原市', '韮崎市', '身延町', '昭和町',
                    '南部町', '富士川町', '早川町', '道志村', '西桂町', '忍野村', '山中湖村', '小菅村', '丹波山村'
                ]
                matched = None
                for m in sorted(known_munis, key=len, reverse=True):
                    if rest.startswith(m):
                        matched = m
                        break
                if matched and 'さん（' in rest[len(matched):]:
                    person_part = rest[len(matched):].lstrip()
                    self.current_city = self._normalize_municipality(matched)
                    person_info = self._parse_person_info(person_part)
                    if person_info:
                        person_info['地域'] = self.current_region
                        city_val = self.current_city if self.current_city else self.current_region
                        person_info['市町村'] = self._normalize_municipality(city_val)
                        self.data.append(person_info)
                    i += 1
                    continue
                # フォールバック: 'さん（' の直前までで最も自然な区切りを探す（末尾の市/町/村/区 ただしその後 2～4 文字で 'さん（' を含む人名が続く候補を選択）
                if 'さん（' in rest:
                    idx_person = rest.find('さん（')
                    candidate = None
                    for pos in range(idx_person - 1, -1, -1):
                        if rest[pos] in '市町村区':
                            tail = rest[pos+1:idx_person]
                            # 人名仮判定: 1～4 文字程度（姓+名で4～6程度になるが姓のみ/姓+名の前半が入ることを許容）
                            if 0 < len(tail) <= 2:  # 市町村末尾直後すぐ人名開始とみなす
                                candidate = pos
                                break
                    if candidate is not None:
                        city = rest[:candidate+1].strip()
                        person_part = rest[candidate+1:].lstrip()
                        self.current_city = self._normalize_municipality(city)
                        person_info = self._parse_person_info(person_part)
                        if person_info:
                            person_info['地域'] = self.current_region
                            city_val = self.current_city if self.current_city else self.current_region
                            person_info['市町村'] = self._normalize_municipality(city_val)
                            self.data.append(person_info)
                        i += 1
                        continue
                # 上記いずれも失敗した場合は従来通り市町村行として扱う
                self.current_city = self._normalize_municipality(rest)
                i += 1
                continue
            
            # お悔やみ情報の解析
            person_info = self._parse_person_info(line)
            if person_info:
                person_info['地域'] = self.current_region
                # 市町村名は current_city 優先。無ければ地域→市町村対応マップで補完。
                region_city_map = {
                    '甲　府': '甲府市', '甲府': '甲府市',
                    '峡北・甲斐': '', '峡　北': '', '峡　中': '', '峡　南': '', '峡　東': '', '郡　内': ''
                }
                if self.current_city:
                    city_val = self.current_city
                else:
                    city_val = region_city_map.get(self.current_region, self.current_region)
                city_val_norm = self._normalize_municipality(city_val)
                # 甲府地域フォールバック: 空 or "甲府" の場合は甲府市に統一
                if city_val_norm in ('', '甲府') and ('甲' in self.current_region and '府' in self.current_region):
                    city_val_norm = '甲府市'
                person_info['市町村'] = city_val_norm
                self.data.append(person_info)
            
            i += 1
    
    def _parse_person_info(self, line):
        """
        個人のお悔やみ情報を解析
        
        Args:
            line (str): お悔やみ情報の行
            
        Returns:
            dict: 解析された個人情報
        """
        # 特殊文字（☆記号など）を除去
        cleaned_line = re.sub(r'☆（.*?）', '', line)
        
        # 基本パターン: 氏名（ふりがな）[職歴情報。]住所。死亡日。年齢。その他の情報
        # 職歴情報がある場合とない場合の両方に対応
        
        # まず氏名とふりがなを抽出
        name_pattern = r'(.+?)さん（(.+?)）\s*(.+)'
        name_match = re.match(name_pattern, cleaned_line)
        
        if not name_match:
            return None
            
        name = name_match.group(1).strip()
        furigana = name_match.group(2).strip()
        remaining_text = name_match.group(3).strip()
        
        # 残りのテキストを「。」で分割
        parts = remaining_text.split('。')
        if len(parts) < 4:  # 最低でも住所、死亡日、年齢、その他情報が必要
            return None
        
        # 年齢パターンを探して位置を特定
        age_pattern = r'(\d+)歳'
        age_index = -1
        age = 0
        
        for i, part in enumerate(parts):
            age_match = re.search(age_pattern, part)
            if age_match:
                age = int(age_match.group(1))
                age_index = i
                break
        
        if age_index == -1:
            return None
            
        # 年齢の位置に基づいて他の要素を決定
        if age_index >= 3:
            # 職歴情報がある場合: [職歴情報, 住所, 死亡日, 年齢部分, ...]
            occupation_raw = parts[0].strip() if age_index > 2 else ""
            address = parts[age_index - 2].strip()
            death_date = parts[age_index - 1].strip()
        else:
            # 職歴情報がない場合: [住所, 死亡日, 年齢部分, ...]
            occupation_raw = ""
            address = parts[0].strip()
            death_date = parts[1].strip()
        
        # 年齢以降のテキストを結合
        other_info = '。'.join(parts[age_index + 1:])
        
        # 職歴・属性はキーワードで判定せず、該当パートをそのまま採用（喪主関連語が混入している場合のみ除外）
        final_occupation = ""
        if occupation_raw and not any(keyword in occupation_raw for keyword in ['喪主', '長男', '長女', '次男', '次女', '夫', '妻', '父', '母']):
            final_occupation = occupation_raw.strip()

        # 喪主情報を先に抽出
        chief_mourner = self._extract_chief_mourner(other_info)
        
        # 追加抽出は行わない（決め打ちせず、元テキスト優先）。
        
        # 通夜・告別式情報を抽出
        wake_info = self._extract_wake_info(other_info)
        funeral_info = self._extract_funeral_info(other_info)
        venue = self._extract_venue(other_info)
        
        # 関係者情報を抽出
        relatives = self._extract_relatives(other_info)
        
        return {
            '氏名': name,
            'ふりがな': furigana,
            '住所': address,
            '死亡日': death_date,
            '年齢': age,
            '職歴・属性': final_occupation,
            '通夜': wake_info,
            '告別式': funeral_info,
            '会場': venue,
            '関係者': relatives,
            '喪主': chief_mourner
        }
    
    def _extract_occupation(self, text):
        """
        職歴・属性を抽出（喪主情報を完全に除外）
        """
        # まず喪主情報を完全に除外
        mourner_patterns = [
            r'喪主は[^。]*?(?:さん|氏)',
            r'喪主は[^。]*?で[^。]*?(?:さん|氏)',
            r'喪主は[^。]*?で[^。]*?勤務[^。]*?(?:さん|氏)'
        ]
        
        text_without_mourner = text
        for pattern in mourner_patterns:
            text_without_mourner = re.sub(pattern, '', text_without_mourner)
        
        # 「元○○」「○○勤務」「○○代表」「○○取締役」「○○教諭」「自営業」「○○行員」「○○警部補」などのパターン
        occupation_patterns = [
            r'元([^。、]+?)勤務',
            r'元([^。、喪]+?)(?:会社|銀行|病院|学校|役所)',
            r'元([^。、喪]+?)(?!さん|氏)',
            r'([^。、喪]+?)代表取締役',
            r'([^。、喪]+?)代表(?!取締役)',
            r'([^。、喪]+?)勤務(?!.+?さん)',
            r'([^。、喪]+?)(?:会社|銀行|病院)(?!.+?さん)',
            r'([^。、喪]+?)(?:取締役|教諭|行員|警部補|部長|課長|主任)(?!.+?さん)',
            r'(自営業)'
        ]
        
        for pattern in occupation_patterns:
            match = re.search(pattern, text_without_mourner)
            if match:
                occupation = match.group(1).strip()
                # 除外すべき文字列をチェック
                exclude_keywords = ['さん', '氏', '君', '喪主', '長男', '長女', '次男', '次女', '夫', '妻', '父', '母']
                if not any(keyword in occupation for keyword in exclude_keywords) and len(occupation) > 1:
                    # さらに喪主関連の文字列が含まれていないかチェック
                    if '喪主' not in occupation and occupation not in ['長男', '長女', '次男', '次女', '夫', '妻']:
                        return occupation
        
        return ""
    
    def _extract_wake_info(self, text):
        """
        通夜情報を抽出
        """
        wake_match = re.search(r'通夜([^、。]+)', text)
        return wake_match.group(1).strip() if wake_match else ""
    
    def _extract_funeral_info(self, text):
        """
        告別式情報を抽出
        """
        funeral_match = re.search(r'告別式([^、。]+)', text)
        return funeral_match.group(1).strip() if funeral_match else ""
    
    def _extract_venue(self, text):
        """
        会場情報を抽出
        """
        # 「○○ホール」「○○会館」などの会場名
        venue_patterns = [
            r'([^、。]*?ホール[^、。]*)',
            r'([^、。]*?会館[^、。]*)',
            r'([^、。]*?セレモニー[^、。]*)',
            r'([^、。]*?シティホール[^、。]*)'
        ]
        
        for pattern in venue_patterns:
            match = re.search(pattern, text)
            if match:
                venue = match.group(1).strip()
                # 不要な部分を除去
                venue = re.sub(r'\(斎場の地図はこちら\)', '', venue).strip()
                return venue
        
        return ""
    
    def _extract_relatives(self, text):
        """
        関係者情報を抽出（喪主情報は除外）。
        キーワードで決め打ちせず、原文の文節をそのまま採用。
        具体的には、
        - 喪主節を除いた残りを「、」「。」で区切り、
        - 「さん」または「氏」を含む文節を、そのまま収集する。
        """
        relatives: list[str] = []
        seen_keys: set[str] = set()

        # 喪主情報を除外
        text_without_mourner = re.sub(r'喪主は[^。]*?(?:さん|氏)', '', text)

        def _canon(s: str) -> str:
            # 全角スペース除去 + すべての空白除去 + 読点の正規化 + 末尾の「さん/氏」を除去
            t = s.replace('\u3000', ' ')
            t = re.sub(r'\s+', '', t)
            t = t.replace('，', '、')
            t = re.sub(r'(さん|氏)$', '', t)
            return t

        # 区切って「さん/氏」を含む文節をそのまま採用
        segments = re.split(r'[、。]+', text_without_mourner)
        for seg in segments:
            s = seg.strip()
            if not s:
                continue
            # 「通夜」「告別式」「会場」などは除外（関係者ではない）
            if any(h in s for h in ['通夜', '告別式', '会場']):
                continue
            if ('さん' in s) or ('氏' in s):
                key = _canon(s)
                if key and key not in seen_keys:
                    relatives.append(s)
                    seen_keys.add(key)

        return '、'.join(relatives) if relatives else ""
    
    def _extract_chief_mourner(self, text):
        """
        喪主情報を抽出
        """
        # より詳細なパターンマッチング
        mourner_patterns = [
            # 「喪主は長男で○○勤務△△さん」のパターン
            r'喪主は(.+?)で(.+?)勤務(.+?)さん',
            # 「喪主は長男で○○△△さん」のパターン  
            r'喪主は(.+?)で(.+?)(.+?)さん',
            # 「喪主は○○勤務△△さん」のパターン
            r'喪主は(.+?)勤務(.+?)さん',
            # 「喪主は△△さん」のパターン
            r'喪主は(.+?)さん'
        ]
        
        for pattern in mourner_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # 関係性、職場、名前の場合
                    relation = groups[0].strip()
                    workplace = groups[1].strip()
                    name = groups[2].strip()
                    return f"{relation} {name}（{workplace}勤務）"
                elif len(groups) == 2:
                    # 2つの情報がある場合
                    if '勤務' in pattern:
                        # 職場と名前
                        workplace = groups[0].strip()
                        name = groups[1].strip()
                        return f"{name}（{workplace}勤務）"
                    else:
                        # 関係性と職場+名前、または関係性と名前
                        relation = groups[0].strip()
                        workplace_name = groups[1].strip()
                        # 職場名が含まれているかチェック
                        if any(keyword in workplace_name for keyword in ['勤務', '会社', '銀行', '病院', '役所', '建設']):
                            return f"{relation} {workplace_name}"
                        else:
                            return f"{relation} {workplace_name}"
                else:
                    # 名前のみ
                    return groups[0].strip()
        
        return ""
    
    def save_to_csv(self, data, output_path):
        """
        データをCSVファイルに保存
        
        Args:
            data (list): お悔やみ情報のリスト
            output_path (str): 出力ファイルのパス
        """
        try:
            if not data:
                print("保存するデータがありません")
                return
            
            # DataFrameを作成
            df = pd.DataFrame(data)
            
            # 列の順序を指定
            columns_order = [
                '地域', '市町村', '氏名', 'ふりがな', '住所', '死亡日', '年齢',
                '職歴・属性', '喪主', '関係者', '通夜', '告別式', '会場'
            ]
            
            # 存在する列のみを選択
            existing_columns = [col for col in columns_order if col in df.columns]
            df = df[existing_columns]
            
            # 優先度に基づいてソート
            def get_priority(row):
                return compute_priority(row)
            
            # 元の順序を保持するためのインデックスを追加
            df = df.reset_index(drop=True)
            df['_original_order'] = df.index
            
            # 優先度を計算してソート
            df['_priority'] = df.apply(get_priority, axis=1)
            df_sorted = df.sort_values(['_priority', '_original_order'])  # 優先度、元の順序でソート
            df_sorted = df_sorted.drop(columns=['_priority', '_original_order'])  # 作業用列を削除
            
            # CSVファイルに保存
            df_sorted.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"CSVファイルを保存しました: {output_path}")
            
            # 統計情報を表示
            self._print_statistics(df_sorted)
            # 関係者の非空件数を簡易表示（検証用）
            try:
                if '関係者' in df_sorted.columns:
                    import pandas as _pd
                    non_empty = _pd.to_numeric(_pd.Series([0]))  # dummy to ensure _pd is used
                    rel = df_sorted['関係者'].fillna('').astype(str).str.strip()
                    cnt = int((rel != '').sum())
                    print(f"関係者（非空）: {cnt}/{len(df_sorted)} 件")
            except Exception:
                pass
            
        except Exception as e:
            print(f"CSV保存エラー: {e}")
    
    def save_to_excel(self, data, output_path):
        """
        データをExcelファイルに保存（市町村別にシート分割）
        
        Args:
            data (list): お悔やみ情報のリスト
            output_path (str): 出力ファイルのパス
        """
        try:
            if not data:
                print("保存するデータがありません")
                return
            
            # DataFrameを作成
            df = pd.DataFrame(data)
            
            # 列の順序を指定
            columns_order = [
                '地域', '市町村', '氏名', 'ふりがな', '住所', '死亡日', '年齢',
                '職歴・属性', '喪主', '関係者', '通夜', '告別式', '会場'
            ]
            
            # 存在する列のみを選択
            existing_columns = [col for col in columns_order if col in df.columns]
            df = df[existing_columns]
            
            # 優先度に基づいてソート
            def get_priority(row):
                return compute_priority(row)
            
            # 元の順序を保持するためのインデックスを追加
            df = df.reset_index(drop=True)
            df['_original_order'] = df.index
            
            # 優先度を計算してソート
            df['_priority'] = df.apply(get_priority, axis=1)
            df_sorted = df.sort_values(['_priority', '_original_order'])  # 優先度、元の順序でソート
            df_sorted = df_sorted.drop(columns=['_priority', '_original_order'])  # 作業用列を削除
            
            # Excelファイルに保存（市町村別にシート分割）
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 全体のシート（優先度ソート適用）
                df_sorted.to_excel(writer, sheet_name='全体', index=False)
                
                # 市町村別のシート（市町村内でも優先度ソート適用）
                for city in df_sorted['市町村'].unique():
                    if city:  # 空でない場合のみ
                        city_df = df_sorted[df_sorted['市町村'] == city].copy()
                        
                        # シート名の長さ制限と無効文字の除去
                        sheet_name = city[:31].replace('/', '_').replace('\\', '_')
                        city_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"Excelファイルを保存しました: {output_path}")
            
            # 統計情報を表示
            self._print_statistics(df_sorted)
            
        except Exception as e:
            print(f"Excel保存エラー: {e}")
    
    def save_to_markdown(self, data, output_path):
        """
        データをGitHub Pages用のMarkdownファイルに保存
        
        Args:
            data (list): お悔やみ情報のリスト
            output_path (str): 出力ファイルのパス
        """
        try:
            if not data:
                print("保存するデータがありません")
                return
            
            # DataFrameを作成
            df = pd.DataFrame(data)
            
            # 列の順序を指定
            columns_order = [
                '地域', '市町村', '氏名', 'ふりがな', '住所', '死亡日', '年齢',
                '職歴・属性', '喪主', '関係者', '通夜', '告別式', '会場'
            ]
            
            # 存在する列のみを選択
            existing_columns = [col for col in columns_order if col in df.columns]
            df = df[existing_columns]
            
            # 優先度に基づいてソート
            def get_priority(row):
                return compute_priority(row)
            
            # 元の順序を保持するためのインデックスを追加
            df = df.reset_index(drop=True)
            df['_original_order'] = df.index
            
            # 優先度を計算してソート
            df['_priority'] = df.apply(get_priority, axis=1)
            df_sorted = df.sort_values(['_priority', '_original_order'])  # 優先度、元の順序でソート
            df_sorted = df_sorted.drop(columns=['_priority', '_original_order'])  # 作業用列を削除

            # LINE通知はGitHub Pagesへの公開後（約2分後）に送信するため、ここでは送信しない
            
            # Markdownファイルとして保存
            with open(output_path, 'w', encoding='utf-8') as f:
                fm = build_front_matter(f'お悔やみ情報 ({get_jp_date()})', datetime.now(), layout='default')
                f.write(fm)
                
                # CSSスタイルを追加（モバイル最適化）
                f.write('<style>\n')
                f.write('@media (max-width: 768px) {\n')
                f.write('  .compact-table { font-size: 12px; }\n')
                f.write('  .compact-table th, .compact-table td { padding: 4px !important; }\n')
                f.write('  .responsive-table { overflow-x: auto; -webkit-overflow-scrolling: touch; }\n')
                f.write('  table { min-width: auto !important; }\n')
                f.write('}\n')
                f.write('</style>\n\n')
                
                # タイトル
                f.write(f'# お悔やみ情報 ({get_jp_date()})\n\n')
                # 統計情報と市町村別人数はWebには掲載しない（LINEに通知済み）
                
                # 全体テーブル（簡易版のみ）
                f.write('## 全体一覧（簡易版）\n\n')
                self._write_compact_table(f, df_sorted)
                
                # 市町村別一覧はWeb掲載しない
                
                # フッター
                f.write('---\n')
                f.write(f'*最終更新: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}*\n')
            
            print(f"Markdownファイルを保存しました: {output_path}")
            
            # 統計情報を表示
            self._print_statistics(df_sorted)
            
        except Exception as e:
            print(f"Markdown保存エラー: {e}")

    # LINE Notify は使用しないため削除（Messaging API のみ使用）

    def _send_line_messaging(self, message: str) -> bool:
        """LINE Messaging API でメッセージ送信（Push message）
        env:
          LINE_MESSAGING_CHANNEL_ACCESS_TOKEN, LINE_MESSAGING_TO(カンマ区切り)
        config.ini:
          [line_messaging] enabled, channel_access_token, to
        戻り値: 送信を試み送れたら True、未設定や失敗で False
        """
        enabled: bool = True
        token: Optional[str] = os.getenv('LINE_MESSAGING_CHANNEL_ACCESS_TOKEN')
        to_raw: Optional[str] = os.getenv('LINE_MESSAGING_TO')
        recipients = []
        if not token or not to_raw:
            cfg = configparser.ConfigParser()
            if os.path.exists('config.ini'):
                try:
                    cfg.read('config.ini', encoding='utf-8')
                    enabled = cfg.getboolean('line_messaging', 'enabled', fallback=True)
                    token = token or cfg.get('line_messaging', 'channel_access_token', fallback='').strip()
                    to_raw = to_raw or cfg.get('line_messaging', 'to', fallback='').strip()
                except Exception:
                    pass
        if not enabled:
            return False
        if not token or not to_raw:
            return False
        # ダブルクオートで囲まれている場合は除去
        if token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        # 宛先のダブルクオート除去
        if to_raw.startswith('"') and to_raw.endswith('"'):
            to_raw = to_raw[1:-1]
        recipients = [r.strip().strip('"') for r in to_raw.split(',') if r.strip()]
        # 宛先IDの形式を簡易検証（U/G/R + 32桁）
        import re as _re
        invalid_ids = [rid for rid in recipients if not _re.fullmatch(r'[UGR][0-9a-fA-F]{32}', rid)]
        if invalid_ids:
            print(f"LINE Messaging設定警告: 宛先IDの形式が不正: {', '.join(invalid_ids)}")
            print("例: ユーザーIDは U で始まる 33 文字。表示名では送れません。")
        # 送信前にトークンの有効性を軽く検査
        try:
            if requests:
                info_resp = requests.get('https://api.line.me/v2/bot/info', headers={'Authorization': f'Bearer {token}'}, timeout=8)
                if info_resp.status_code == 401:
                    print('LINE Messagingトークン無効: チャネルアクセストークンを再発行（Messaging APIの長期トークン）してください。')
                    return False
        except Exception:
            # ネットワーク不通などは続行（本送信で再評価）
            pass
        if not recipients:
            return False
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        payload_template = {
            'to': None,
            'messages': [
                {
                    'type': 'text',
                    'text': message
                }
            ]
        }
        try:
            import json as _json
            sent_any = False
            if requests:
                for rid in recipients:
                    payload = dict(payload_template)
                    payload['to'] = rid
                    r = requests.post(url, headers=headers, data=_json.dumps(payload), timeout=10)
                    if r.status_code == 200:
                        sent_any = True
                    else:
                        if r.status_code == 401:
                            print('LINE Messaging送信失敗(401): 認証エラー。以下を確認してください:')
                            print(' - Messaging APIのチャネルアクセストークン（長期）を使用しているか')
                            print(' - トークンのチャネルが正しいか（別チャネルのトークンでは不可）')
                            print(' - 宛先IDが U/G/R で始まる正しいIDか（表示名不可）')
                            print(' - 受信者がBotを友だち追加/グループへ招待済みか（Push許可）')
                        else:
                            print(f'LINE Messaging送信失敗: {r.status_code} {getattr(r,"text","")[:200]}')
            else:
                import urllib.request, urllib.error
                for rid in recipients:
                    payload = dict(payload_template)
                    payload['to'] = rid
                    data = _json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(url, data=data, method='POST', headers=headers)
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            if resp.status == 200:
                                sent_any = True
                            else:
                                print(f'LINE Messaging送信失敗: {resp.status}')
                    except urllib.error.HTTPError as he:
                        print(f'LINE Messaging送信HTTPエラー: {he.code}')
                    except Exception as e:
                        print(f'LINE Messaging送信エラー: {e}')
            if sent_any:
                print('LINE Messaging APIで通知を送信しました')
            return sent_any
        except Exception as e:
            print(f'LINE Messaging送信例外: {e}')
            return False

    def _build_stats_message(self, df: pd.DataFrame) -> str:
        """統計情報のLINE通知文面を生成"""
        if df.empty:
            return ''
        post_url = self._get_today_post_url()
        # 安全に数値化
        ages_series = df['年齢'] if '年齢' in df.columns else pd.Series(dtype='float64')
        ages = pd.to_numeric(ages_series, errors='coerce')
        total = len(df)
        mean_age = ages.mean()
        max_age = ages.max()
        min_age = ages.min()
        # 市町村別人数
        city_counts = df['市町村'].value_counts().sort_index() if '市町村' in df.columns else {}
        date_str = datetime.now().strftime('%Y-%m-%d')
        lines = [
            post_url,
            '',
            f'【お悔やみ情報 {date_str}】',
            '統計情報',
            f'- 総人数: {total}名',
            f'- 平均年齢: {mean_age:.1f}歳' if pd.notna(mean_age) else '- 平均年齢: -',
            f'- 最高年齢: {int(max_age)}歳' if pd.notna(max_age) else '- 最高年齢: -',
            f'- 最低年齢: {int(min_age)}歳' if pd.notna(min_age) else '- 最低年齢: -',
            '',
            '市町村別人数',
        ]
        if hasattr(city_counts, 'items'):
            for city, count in city_counts.items():
                lines.append(f'- {city}: {count}名')
        msg = '\n'.join(lines)
        # LINE Notifyの上限対策（1000文字程度）
        return msg[:950]
    
    def _write_compact_table(self, f, df):
        """コンパクトなテーブルを書き込む（モバイル最適化）"""
        f.write('<div class="responsive-table" style="overflow-x: auto; max-width: 100%; margin-bottom: 20px;">\n')
        f.write('<table class="compact-table" style="width: 100%; border-collapse: collapse; font-size: 14px; min-width: 300px;">\n')
        
        # ヘッダー（簡略版）
        f.write('<thead>\n<tr style="background-color: #f0f0f0; border-bottom: 2px solid #ddd;">\n')
        # 氏名, 年齢, 住所(=市町村+住所), 関係者
        compact_headers = ['氏名', '年齢', '住所', '関係者']
        for header in compact_headers:
            f.write(f'<th style="padding: 8px; text-align: left; border: 1px solid #ddd; font-weight: bold;">{header}</th>\n')
        f.write('</tr>\n</thead>\n')
        
        # データ行
        f.write('<tbody>\n')
        for _, row in df.iterrows():
            f.write('<tr style="border-bottom: 1px solid #eee;">\n')
            # 氏名（太字・改行禁止）
            name = row['氏名'] if pd.notna(row['氏名']) else ''
            f.write(f'<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; white-space: nowrap;">{name}</td>\n')

            # 年齢
            age = row['年齢'] if pd.notna(row['年齢']) else ''
            f.write(f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{age}</td>\n')
            
            # 住所（= 市町村 + 住所 を連結、重複回避し簡略表示）
            city = row['市町村'] if ('市町村' in row and pd.notna(row['市町村'])) else ''
            address_raw = row['住所'] if pd.notna(row['住所']) else ''
            merged_addr = ''
            if city and address_raw:
                addr_str = str(address_raw)
                city_str = str(city)
                if addr_str.startswith(city_str):
                    merged_addr = addr_str
                else:
                    merged_addr = f"{city_str}{addr_str}"
            elif city:
                merged_addr = str(city)
            else:
                merged_addr = str(address_raw)
            # 簡略表示（モバイル最適化のため）
            if len(merged_addr) > 15:
                merged_addr = merged_addr[:15] + '...'
            f.write(f'<td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{merged_addr}</td>\n')
            
            # 関係者（省略せず全件。一人1行表示）
            relatives = row['関係者'] if ('関係者' in row and pd.notna(row['関係者'])) else ''
            rel_html = ''
            if isinstance(relatives, str) and relatives:
                # 全角読点「、」またはカンマで分割し、1人1行に（重複排除）
                sep_normalized = relatives.replace('，', '、')
                raw_parts = [p.strip() for p in sep_normalized.split('、') if p.strip()]
                seen_keys = set()
                uniq_parts = []
                for p in raw_parts:
                    key = re.sub(r'\s+', '', p.replace('\u3000', ' '))
                    key = key.replace('，', '、')
                    key = re.sub(r'(さん|氏)$', '', key)
                    if key and key not in seen_keys:
                        uniq_parts.append(p)
                        seen_keys.add(key)
                rel_html = '<br>'.join(uniq_parts) if uniq_parts else relatives
            f.write(f'<td style="padding: 8px; border: 1px solid #ddd; font-size: 12px; line-height: 1.3; white-space: normal;">{rel_html}</td>\n')
            f.write('</tr>\n')
        
        f.write('</tbody>\n</table>\n</div>\n\n')
    
    def _write_markdown_table(self, f, df):
        """
        DataFrameをMarkdownテーブル形式で書き出し（レスポンシブ対応）
        
        Args:
            f: ファイルハンドル
            df: DataFrame
        """
        if df.empty:
            f.write('データがありません。\n')
            return
        
        # スクロール可能なテーブル用のHTMLタグを追加（kramdownでMarkdownを解釈させる）
        f.write('<div class="responsive-table" markdown="1" style="overflow-x: auto; max-width: 100%;">\n\n')
        
        # ヘッダー行
        headers = df.columns.tolist()
        f.write('| ' + ' | '.join(headers) + ' |\n')
        f.write('|' + '|'.join(['---'] * len(headers)) + '|\n')
        
        # データ行
        for _, row in df.iterrows():
            values = []
            for col in headers:
                value = str(row[col]) if pd.notna(row[col]) and row[col] != '' else '-'
                # Markdownのパイプ文字をエスケープ
                value = value.replace('|', '\\|')
                # 長いテキストを短縮（30文字を超える場合）
                if len(value) > 30:
                    value = value[:27] + '...'
                values.append(value)
            f.write('| ' + ' | '.join(values) + ' |\n')
        
        f.write('\n</div>\n\n')
    
    def _print_statistics(self, df):
        """
        統計情報を表示
        
        Args:
            df (DataFrame): お悔やみ情報のDataFrame
        """
        print(f"\n=== 統計情報 ===")
        print(f"総人数: {len(df)}名")
        print(f"平均年齢: {df['年齢'].mean():.1f}歳")
        print(f"最高年齢: {df['年齢'].max()}歳")
        print(f"最低年齢: {df['年齢'].min()}歳")
        
        print(f"\n=== 市町村別人数 ===")
        city_counts = df['市町村'].value_counts()
        for city, count in city_counts.items():
            print(f"{city}: {count}名")


def main():
    """
    メイン関数
    """
    import sys
    import argparse
    import glob
    
    # コマンドライン引数の解析（常にパースしてデフォルト値を持たせる）
    parser = argparse.ArgumentParser(description="お悔やみ情報解析・整理スクリプト")
    parser.add_argument('--auto', action='store_true', help='自動モード（最新ファイルを自動選択）')
    parser.add_argument('--file', type=str, help='入力ファイルのパス')
    parser.add_argument('--output-dir', type=str, default='./okuyami_output', help='出力ディレクトリ')
    args = parser.parse_args()
    
    # 引数がない場合はインタラクティブモード
    if len(sys.argv) == 1:
        print("お悔やみ情報解析・整理スクリプト")
        print("=" * 40)
        
        # 入力ファイルのパスを指定
        input_file = input("入力ファイルのパスを入力してください（Enter で ./okuyami_data/okuyami_20250806.txt）: ").strip()
        if not input_file:
            input_file = "./okuyami_data/okuyami_20250806.txt"
    else:
        # コマンドライン引数モード
        
        if args.auto:
            # 自動モード: 本日分があれば最優先で選択、なければ最新を選択
            pattern = "./okuyami_data/okuyami_*.txt"
            files = glob.glob(pattern)
            if not files:
                print(f"エラー: お悔やみデータファイルが見つかりません: {pattern}")
                sys.exit(1)

            # 今日の日付に一致するファイル名を優先
            today_compact = datetime.now().strftime("%Y%m%d")
            preferred = os.path.join("./okuyami_data", f"okuyami_{today_compact}.txt")
            if os.path.exists(preferred):
                input_file = preferred
                print(f"自動モード: 本日分を優先選択 - {input_file}")
            else:
                # 最新のファイルを選択（ファイル名でソート）
                input_file = max(files)
                print(f"自動モード: 最新ファイルを選択 - {input_file}")
        elif args.file:
            input_file = args.file
        else:
            print("エラー: --auto または --file オプションを指定してください")
            sys.exit(1)
    
    # ファイルの存在確認
    if not os.path.exists(input_file):
        print(f"ファイルが見つかりません: {input_file}")
        sys.exit(1)
    
    # パーサーを作成して解析実行
    parser_obj = OkuyamiParser()
    data = parser_obj.parse_file(input_file)

    # 新聞休刊日など明示メッセージを検知（テキスト全体で判定）
    is_holiday = False
    try:
        with open(input_file, 'r', encoding='utf-8') as _rf:
            raw_txt = _rf.read()
            if '休刊日' in raw_txt or '掲載はありません' in raw_txt:
                is_holiday = True
    except Exception:
        pass

    if not data:
        if is_holiday:
            print('新聞休刊日のため掲載なし（検知）')
        else:
            print("お悔やみ情報が見つかりませんでした")
        # 解析対象ファイルは存在するが有効なお悔やみエントリが無い場合は 2 を返す
        # 1 は異常エラーとの区別用（バッチ側で no-data 通知を送るか判定）
        sys.exit(2)
    
    print(f"\n{len(data)}件のお悔やみ情報を解析しました")
    
    # 出力ファイル名を生成
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 出力ディレクトリを作成
    if len(sys.argv) > 1:
        # 引数モード
        output_dir = args.output_dir
    else:
        # 対話モードのデフォルト
        output_dir = "./okuyami_output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # CSVファイルに保存
        csv_output = os.path.join(output_dir, f"{base_name}_parsed_{timestamp}.csv")
        parser_obj.save_to_csv(data, csv_output)
        
        # Markdownファイルに保存（GitHub Pages用）
        markdown_output = os.path.join(output_dir, f"{base_name}_parsed_{timestamp}.md")
        parser_obj.save_to_markdown(data, markdown_output)
        
        print(f"\n出力ディレクトリ: {output_dir}")
        print("解析・フォーマット処理が正常に完了しました")
        # バッチ側で確実に件数抽出できるASCIIタグ行を出力
        try:
            print(f"ENTRY_COUNT={len(data)}")
        except Exception:
            print("ENTRY_COUNT=")
        
    except Exception as e:
        print(f"出力エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

