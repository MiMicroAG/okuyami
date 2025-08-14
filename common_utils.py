#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共通ユーティリティ関数
- サイトURL取得
- 本日ポストURL生成
- 優先度計算
他スクリプト (parse_and_format_obituary.py, send_line_stats.py など) から利用。
"""
from __future__ import annotations
from datetime import datetime
import os
import re
from typing import Any, Dict

__all__ = [
    'get_site_url', 'get_today_post_url', 'compute_priority'
]

_DEF_SITE = 'https://MiMicroAG.github.io/okuyami-info'


def get_site_url() -> str:
    env_url = os.getenv('OKUYAMI_SITE_URL')
    if env_url and env_url.strip():
        return env_url.strip().rstrip('/')
    cfg_path = os.path.join(os.path.dirname(__file__), 'okuyami-info', '_config.yml')
    site = _DEF_SITE
    try:
        if os.path.exists(cfg_path):
            url_val, baseurl_val = '', ''
            with open(cfg_path, 'r', encoding='utf-8') as yf:
                for line in yf:
                    m = re.match(r"\s*url:\s*\"?([^\"\n#]+)\"?", line)
                    if m:
                        url_val = m.group(1).strip()
                    m2 = re.match(r"\s*baseurl:\s*\"?([^\"\n#]+)\"?", line)
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
    return site.rstrip('/')


def get_today_post_url(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    site = get_site_url()
    return f"{site}/posts/{dt.strftime('%Y/%m/%d')}/okuyami-info/"


# DataFrame 行 (Series) または dict を受け取って優先度を返す
# 1: NEC/ＮＥＣ を含む, 2: 中央市, 3: その他

def compute_priority(row: Any) -> int:
    try:
        get = row.get if hasattr(row, 'get') else (lambda k, d=None: row[k] if k in row else d)
        text_fields = [str(get('氏名', '')), str(get('職歴・属性', '')), str(get('関係者', '')), str(get('喪主', ''))]
        full_text = ' '.join(text_fields)
        if 'ＮＥＣ' in full_text or 'NEC' in full_text:
            return 1
        city = str(get('市町村', ''))
        if city == '中央市':
            return 2
        return 3
    except Exception:
        return 99
