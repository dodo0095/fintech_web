"""從證交所 ISIN 清單產生 ETF 名單（公司/ETF上市.csv、公司/ETF上櫃.csv）。

原本的 公司/上市.csv、上櫃.csv 只有股票，沒有 ETF，導致回測頁搜不到 0050、00878。
用法：python manage.py refresh_etf_list
"""
from __future__ import annotations

import csv
import io
import os
import re

import pandas as pd
import requests
from django.core.management.base import BaseCommand, CommandError

from news import tickers

SOURCES = (
    (2, "ETF上市.csv"),  # 上市 → .TW
    (4, "ETF上櫃.csv"),  # 上櫃 → .TWO
)
URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
SECTION = "ETF"


def parse_etfs(html: str) -> list[tuple[str, str, str]]:
    """回傳 [(代號, 名稱, 上市日)]；只取「ETF」區段。"""
    df = pd.read_html(io.StringIO(html), header=0)[0]
    first = df.columns[0]
    section = None
    out = []
    for _, row in df.iterrows():
        head = str(row[first]).strip()
        vals = [str(v).strip() for v in row.values[:3]]
        if len(set(vals)) == 1:  # 區段標題列：整列同一個字串
            section = head
            continue
        if section != SECTION:
            continue
        m = re.match(r"^([0-9A-Z]+)[\s　]+(.+)$", head)
        if not m:
            continue
        listed = str(row.get("上市日", "")).strip()
        out.append((m.group(1), m.group(2).strip(), listed))
    return out


class Command(BaseCommand):
    help = "從證交所 ISIN 清單更新 ETF 名單（回測頁搜尋用）"

    def handle(self, *args, **opts):
        base = tickers._COMPANY_DIR
        for mode, fname in SOURCES:
            resp = requests.get(URL.format(mode=mode), timeout=60)
            resp.raise_for_status()
            resp.encoding = "big5hkscs"
            rows = parse_etfs(resp.text)
            if len(rows) < 10:
                raise CommandError(f"{fname}：只解析到 {len(rows)} 檔，網頁格式可能改變，未覆寫")
            path = os.path.join(base, fname)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["代號", "公司名稱", "上市日"])
                w.writerows(rows)
            self.stdout.write(f"{fname}: {len(rows)} 檔 → {path}")
