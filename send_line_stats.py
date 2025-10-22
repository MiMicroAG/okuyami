#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公開後にLINEへ統計情報を送信するスクリプト（約2分遅延はバッチ側で実施）
- 最新のCSV(./okuyami_output/*_parsed_*.csv)を読み、統計を作成
- メッセージ先頭に当日の投稿URLを付与
- GitHub Pagesで新規投稿の公開を確認してからLINE Messaging APIでpush送信
"""
import os
import glob
import configparser
import time
from datetime import datetime
from typing import Optional, List, Tuple
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
def _find_todays_csv(target_dt: Optional[datetime] = None) -> Optional[str]:
    """okuyami_output 内の本日分CSV (okuyami_YYYYMMDD_parsed_*.csv) を探す"""
    if target_dt is None:
        target_dt = datetime.now()
    today_compact = target_dt.strftime('%Y%m%d')
    pattern = os.path.join('./okuyami_output', f'okuyami_{today_compact}_parsed_*.csv')
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)
def _build_stats_message(df: 'pd.DataFrame', target_dt: Optional[datetime] = None) -> str:
    if df.empty:
        return ''
    if target_dt is None:
        target_dt = datetime.now()
    ages_series = df['年齢'] if '年齢' in df.columns else pd.Series(dtype='float64')
    ages = pd.to_numeric(ages_series, errors='coerce')
    total = len(df)
    mean_age = ages.mean()
    max_age = ages.max()
    min_age = ages.min()
    city_counts = df['市町村'].value_counts().sort_index() if '市町村' in df.columns else []
    date_str = target_dt.strftime('%Y-%m-%d')
    lines = [
        _get_today_post_url(target_dt),
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
def _add_cache_buster(url: str, attempt: int) -> str:
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}_ts={int(time.time())}_{attempt}"
def _http_get(url: str) -> Tuple[int, str]:
    headers = {
        'User-Agent': 'okuyami-bot/1.0 (+https://github.com/MiMicroAG/okuyami)',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    if requests:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code, response.text or ''
    import urllib.request
    import urllib.error
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # type: ignore[arg-type]
            charset = resp.headers.get_content_charset() or 'utf-8'
            data = resp.read()
            try:
                text = data.decode(charset, errors='replace')
            except LookupError:
                text = data.decode('utf-8', errors='replace')
            status = getattr(resp, 'status', resp.getcode())
            return status, text
    except urllib.error.HTTPError as he:  # type: ignore[attr-defined]
        data = he.read() if hasattr(he, 'read') else b''
        charset = he.headers.get_content_charset() if getattr(he, 'headers', None) else 'utf-8'
        try:
            text = data.decode(charset or 'utf-8', errors='replace')
        except LookupError:
            text = data.decode('utf-8', errors='replace')
        return he.code, text
def _ensure_site_publication(target_dt: datetime, *, extra_markers: Optional[List[str]] = None,
                             timeout: Optional[int] = None, interval: Optional[int] = None) -> bool:
    if timeout is None:
        timeout = int(os.getenv('OKUYAMI_PUBLISH_WAIT_SECONDS', '600'))
    if interval is None:
        interval = int(os.getenv('OKUYAMI_PUBLISH_POLL_INTERVAL', '15'))
    url = _get_today_post_url(target_dt)
    required_marker = f'お悔やみ情報 ({get_jp_date(target_dt)})'
    markers_optional = [m for m in (extra_markers or []) if isinstance(m, str) and m.strip()]
    print(f'GitHub Pages公開確認開始: {url}')
    start = time.monotonic()
    attempt = 0
    last_status: Optional[int] = None
    last_error = ''
    last_snippet = ''
    while time.monotonic() - start <= timeout:
        attempt += 1
        bust_url = _add_cache_buster(url, attempt)
        status: Optional[int] = None
        body = ''
        try:
            status, body = _http_get(bust_url)
        except Exception as exc:
            last_error = f'{type(exc).__name__}: {exc}'
            last_status = None
        else:
            last_status = status
            if status == 200 and body:
                if required_marker in body:
                    elapsed = int(time.monotonic() - start)
                    print(f'公開確認成功: attempt={attempt}, elapsed={elapsed}s, status=200')
                    missing_optional = [m for m in markers_optional if m not in body]
                    if missing_optional:
                        print(f'参考: 以下の確認用文字列は未検出です: {", ".join(missing_optional)}')
                    return True
                last_snippet = body[:200]
        wait_label = status if status is not None else 'error'
        print(f'未確認: attempt={attempt}, status={wait_label} -> {required_marker} 未検出。{interval}s待機。')
        time.sleep(interval)
    print(f'GitHub Pagesの公開確認がタイムアウトしました ({timeout}s)。')
    if last_status is not None:
        print(f'最終ステータス: {last_status}')
    if last_error:
        print(f'最終エラー: {last_error}')
    elif last_snippet:
        print(f'最終応答冒頭: {last_snippet[:120]}...')
    return False
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
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
    if to_raw.startswith('"') and to_raw.endswith('"'):
        to_raw = to_raw[1:-1]
    recipients = [r.strip().strip('"') for r in to_raw.split(',') if r.strip()]
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
        'messages': [{'type': 'text', 'text': message}]
    }
    sent_any = False
    try:
        import json as _json
        if requests:
            for rid in recipients:
                payload = dict(payload_template)
                payload['to'] = rid
                resp = requests.post(url, headers=headers, data=_json.dumps(payload), timeout=10)
                if resp.status_code == 200:
                    sent_any = True
                else:
                    print(f'LINE送信失敗: {resp.status_code} {getattr(resp, "text", "")[:200]}')
        else:
            import urllib.request
            import urllib.error
            for rid in recipients:
                payload = dict(payload_template)
                payload['to'] = rid
                data = _json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, method='POST', headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:  # type: ignore[arg-type]
                        if resp.status == 200:
                            sent_any = True
                        else:
                            print(f'LINE送信失敗: {resp.status}')
                except urllib.error.HTTPError as he:  # type: ignore[attr-defined]
                    print(f'LINE送信HTTPエラー: {he.code}')
                except Exception as exc:
                    print(f'LINE送信エラー: {exc}')
    except Exception as exc:
        print(f'LINE送信例外: {exc}')
        return False
    if sent_any:
        print('LINE Messaging APIで通知を送信しました')
    return sent_any
def main() -> int:
    try:
        target_dt = datetime.now()
        todays_csv = _find_todays_csv(target_dt)
        extra_markers: List[str] = []
        msg: Optional[str] = None
        if todays_csv is None:
            today_str = target_dt.strftime('%Y-%m-%d')
            msg = '\n'.join([
                _get_today_post_url(target_dt),
                '',
                f'【お悔やみ情報 {today_str}】',
                '本日の掲載は確認できませんでした。',
            ])
        else:
            df = pd.read_csv(todays_csv, encoding='utf-8')
            msg = _build_stats_message(df, target_dt)
            if not msg:
                print('送信するメッセージが空のため中止')
                return 0
            if not df.empty and '氏名' in df.columns:
                lead_name = str(df.iloc[0]['氏名']).strip()
                if lead_name:
                    extra_markers.append(lead_name)
        if not msg:
            print('送信メッセージが決定できなかったため終了します')
            return 1
        if not _ensure_site_publication(target_dt, extra_markers=extra_markers):
            print('GitHub Pagesの公開が未確認のため通知をスキップします')
            return 2
        sent = _send_line_messaging(msg)
        return 0 if sent else 1
    except Exception as exc:
        print(f'送信処理エラー: {exc}')
        return 1
if __name__ == '__main__':
    import sys
    if any(arg == '--notify-no-data' for arg in sys.argv[1:]):
        target_dt = datetime.now()
        today_str = target_dt.strftime('%Y-%m-%d')
        msg = '\n'.join([
            _get_today_post_url(target_dt),
            '',
            f'【お悔やみ情報 {today_str}】',
            '本日の掲載は確認できませんでした。',
        ])
        if not _ensure_site_publication(target_dt):
            print('GitHub Pagesの公開が未確認のため、通知(--notify-no-data)をスキップします')
            sys.exit(2)
        ok = _send_line_messaging(msg)
        sys.exit(0 if ok else 1)
    sys.exit(main())
