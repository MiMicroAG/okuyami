#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公開後にLINEへ統計情報を送信するスクリプト（約2分遅延はバッチ側で実施）
- 最新のCSV(./okuyami_output/*_parsed_*.csv)を読み、統計を作成
- メッセージ先頭に当日の投稿URLを付与
- LINE Messaging API で push 送信
"""

import os
import glob
import configparser
from datetime import datetime
from typing import Optional
from common_utils import get_today_post_url, get_site_url, get_jp_date

try:
    import pandas as pd
except Exception as e:
    print(f"pandasの読み込みに失敗: {e}")
    raise

try:
    import requests  # optional
except Exception:
    requests = None  # type: ignore


_get_site_url = get_site_url  # backward compatibility
_get_today_post_url = get_today_post_url


def _find_todays_csv() -> Optional[str]:
    """okuyami_output 内の本日分CSV (okuyami_YYYYMMDD_parsed_*.csv) を探す"""
    today_compact = datetime.now().strftime('%Y%m%d')
    pattern = os.path.join('./okuyami_output', f'okuyami_{today_compact}_parsed_*.csv')
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


def _build_stats_message(df: 'pd.DataFrame') -> str:
    if df.empty:
        return ''
    ages_series = df['年齢'] if '年齢' in df.columns else pd.Series(dtype='float64')
    ages = pd.to_numeric(ages_series, errors='coerce')
    total = len(df)
    mean_age = ages.mean()
    max_age = ages.max()
    min_age = ages.min()
    city_counts = df['市町村'].value_counts().sort_index() if '市町村' in df.columns else []
    date_str = datetime.now().strftime('%Y-%m-%d')
    lines = [
        _get_today_post_url(),
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
    if isinstance(city_counts, list):
        pass
    else:
        for city, count in city_counts.items():
            lines.append(f'- {city}: {count}名')
    msg = '\n'.join(lines)
    return msg[:950]


def _send_line_messaging(message: str) -> bool:
    enabled: bool = True
    token: Optional[str] = os.getenv('LINE_MESSAGING_CHANNEL_ACCESS_TOKEN')
    to_raw: Optional[str] = os.getenv('LINE_MESSAGING_TO')
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
        print('LINE Messaging設定が不足しているため送信しません')
        return False
    # 余計な引用符を除去
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
    if to_raw.startswith('"') and to_raw.endswith('"'):
        to_raw = to_raw[1:-1]
    recipients = [r.strip().strip('"') for r in to_raw.split(',') if r.strip()]

    # 軽いトークン検証
    try:
        if requests:
            info_resp = requests.get('https://api.line.me/v2/bot/info', headers={'Authorization': f'Bearer {token}'}, timeout=8)
            if info_resp.status_code == 401:
                print('LINE Messagingトークン無効。送信中止。')
                return False
    except Exception:
        pass

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload_template = {
        'to': None,
        'messages': [ {'type': 'text', 'text': message} ]
    }
    sent_any = False
    try:
        import json as _json
        if requests:
            for rid in recipients:
                payload = dict(payload_template)
                payload['to'] = rid
                r = requests.post(url, headers=headers, data=_json.dumps(payload), timeout=10)
                if r.status_code == 200:
                    sent_any = True
                else:
                    print(f'LINE送信失敗: {r.status_code} {getattr(r,"text","")[:200]}')
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
                            print(f'LINE送信失敗: {resp.status}')
                except urllib.error.HTTPError as he:
                    print(f'LINE送信HTTPエラー: {he.code}')
                except Exception as e:
                    print(f'LINE送信エラー: {e}')
    except Exception as e:
        print(f'LINE送信例外: {e}')
        return False
    if sent_any:
        print('LINE Messaging APIで通知を送信しました')
    return sent_any


def main():
    try:
        todays_csv = _find_todays_csv()
        if todays_csv is None:
            # 本日分がない場合は、その旨を通知
            today_str = datetime.now().strftime('%Y-%m-%d')
            msg = "\n".join([
                _get_today_post_url(),
                "",
                f"【お悔やみ情報 {today_str}】",
                "本日の掲載は確認できませんでした。",
            ])
            sent = _send_line_messaging(msg)
            return 0 if sent else 1

        # 本日分がある場合は統計を送信
        df = pd.read_csv(todays_csv, encoding='utf-8')
        msg = _build_stats_message(df)
        if not msg:
            print('送信するメッセージが空のため中止')
            return 0
        sent = _send_line_messaging(msg)
        return 0 if sent else 1
    except Exception as e:
        print(f'送信処理エラー: {e}')
        return 1


if __name__ == '__main__':
    import sys
    # 特別モード: 今日の掲載なしを明示通知
    if any(arg == '--notify-no-data' for arg in sys.argv[1:]):
        today_str = datetime.now().strftime('%Y-%m-%d')
        msg = "\n".join([
            _get_today_post_url(),
            "",
            f"【お悔やみ情報 {today_str}】",
            "本日の掲載は確認できませんでした。",
        ])
        ok = _send_line_messaging(msg)
        sys.exit(0 if ok else 1)
    sys.exit(main())
