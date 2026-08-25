"""上市／上櫃／興櫃代碼對照。給個股新聞與河流圖共用。"""
from __future__ import annotations

import csv
import os
import re
from typing import Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_COMPANY_DIR = os.path.join(_BASE, "公司")

# 上市 .TW；上櫃／興櫃 yfinance 多用 .TWO
_FILES = (
    ("上市.csv", "TW"),
    ("上櫃.csv", "TWO"),
    ("興櫃.csv", "TWO"),
)

_CODE_RE = re.compile(r"([0-9]{3,6}[A-Za-z]?)", re.I)

_by_code: Optional[Dict[str, dict]] = None
_by_name: Optional[Dict[str, dict]] = None


def _norm_name(s: str) -> str:
    return re.sub(r"[\s　]+", "", (s or "")).strip().lower()


def _load() -> None:
    global _by_code, _by_name
    if _by_code is not None:
        return
    _by_code = {}
    _by_name = {}
    for fname, suffix in _FILES:
        path = os.path.join(_COMPANY_DIR, fname)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("代號") or "").strip().upper()
                name = (row.get("公司名稱") or "").strip()
                if not code or not name:
                    continue
                info = {
                    "code": code,
                    "name": name,
                    "yahoo": "{}.{}".format(code, suffix),
                    "market": fname.replace(".csv", ""),
                }
                if code not in _by_code:
                    _by_code[code] = info
                nk = _norm_name(name)
                if nk and nk not in _by_name:
                    _by_name[nk] = info


def _normalize_query(query: str) -> str:
    q = (query or "").strip()
    q = re.sub(r"\.(TWO|TW)\s*$", "", q, flags=re.I)
    return q


def lookup(query: str) -> Optional[dict]:
    """Accept '2330', '2330.TW', '2317.TWO', '2330 台積電'. Name optional.

    Numeric codes always resolve (CSV name if known). Yahoo suffix is
    tried as .TW then .TWO by the caller.
    """
    _load()
    q = _normalize_query(query)
    if not q:
        return None
    m = _CODE_RE.search(q)
    if m:
        code = m.group(1).upper()
        info = _by_code.get(code)
        if info:
            return dict(info)
        return {
            "code": code,
            "name": "",
            "yahoo": "{}.TW".format(code),
            "market": "",
        }
    info = _by_name.get(_norm_name(q))
    return dict(info) if info else None


def yahoo_candidates(info: dict) -> List[str]:
    """Preferred exchange first, then the other. User never types TW/TWO."""
    code = (info or {}).get("code") or ""
    if not code:
        return []
    pref = ((info.get("yahoo") or "").split(".")[-1] or "TW").upper()
    if pref == "TWO":
        return ["{}.TWO".format(code), "{}.TW".format(code)]
    return ["{}.TW".format(code), "{}.TWO".format(code)]


def default_focus() -> dict:
    return lookup("2330") or {
        "code": "2330",
        "name": "台積電",
        "yahoo": "2330.TW",
        "market": "上市",
    }


def all_codes() -> List[str]:
    _load()
    return list(_by_code.keys())
