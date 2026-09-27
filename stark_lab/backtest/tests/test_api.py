"""/backtest/ 頁面與 API 測試（假行情，不連網）。

執行：python manage.py test backtest   （需 SECRET_KEY 環境變數或 .env）
"""
from __future__ import annotations

import json
from datetime import timedelta
from unittest import mock

import numpy as np
import pandas as pd
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from backtest import prices, views
from backtest.models import PriceCache


def fake_df(seed=3, n=1500):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.018, n)))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    open_ = close * (1 + rng.normal(0, 0.004, n))
    return pd.DataFrame({
        "open": open_,
        "high": np.maximum(open_, close) * 1.01,
        "low": np.minimum(open_, close) * 0.99,
        "close": close,
        "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
    }, index=idx)


def fake_downloader(symbol):
    if symbol.endswith(".TWO") and symbol.startswith("2330"):
        return pd.DataFrame()
    return fake_df(seed=len(symbol))


MA_CROSS = {
    "entry": {"logic": "all", "conditions": [{
        "left": {"kind": "ind", "name": "sma", "params": {"period": 5}}, "op": "cross_up",
        "right": {"kind": "ind", "name": "sma", "params": {"period": 20}}}]},
    "exit": {"logic": "any", "conditions": [{
        "left": {"kind": "ind", "name": "sma", "params": {"period": 5}}, "op": "cross_down",
        "right": {"kind": "ind", "name": "sma", "params": {"period": 20}}}]},
    "risk": {"stop_loss": 10},
}


@mock.patch.object(prices, "_download", side_effect=fake_downloader)
class BacktestApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.c = Client()

    def post(self, payload, client=None):
        return (client or self.c).post("/backtest/api/run", data=json.dumps(payload), content_type="application/json")

    def test_page_renders_with_meta_and_csrf_cookie(self, _dl):
        r = self.c.get("/backtest/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="bt-meta"')
        self.assertContains(r, "ma_cross")  # json_script 會把中文轉成 \uXXXX
        self.assertIn("csrftoken", r.cookies)

    def test_search_by_code_and_name(self, _dl):
        r = self.c.get("/backtest/api/search", {"q": "2330"}).json()
        self.assertEqual(r["results"][0]["code"], "2330")
        r = self.c.get("/backtest/api/search", {"q": "台積"}).json()
        self.assertIn("2330", [x["code"] for x in r["results"]])
        self.assertEqual(self.c.get("/backtest/api/search", {"q": ""}).json()["results"], [])

    def test_search_finds_etfs(self, _dl):
        # 公司/上市.csv 不含 ETF；ETF 名單來自 公司/ETF上市.csv、ETF上櫃.csv
        r = self.c.get("/backtest/api/search", {"q": "元大台灣50"}).json()
        self.assertEqual(r["results"][0]["code"], "0050")
        r = self.c.get("/backtest/api/search", {"q": "00679B"}).json()
        self.assertEqual(r["results"][0]["code"], "00679B")

    def test_run_ok(self, dl):
        r = self.post({"symbol": "2330", "strategy": MA_CROSS})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["stock"]["code"], "2330")
        self.assertGreater(d["stats"]["strategy"]["trades"], 0)
        self.assertIn("benchmark", d["stats"])  # 0050 基準
        self.assertEqual(len(d["curve"]["dates"]), len(d["curve"]["strategy"]))
        # 預設近 5 年
        self.assertGreaterEqual(d["period"]["start"], str(pd.Timestamp.today().year - 5))

    def test_price_cache_reused(self, dl):
        self.post({"symbol": "2330", "strategy": MA_CROSS})
        n = dl.call_count
        self.post({"symbol": "2330", "strategy": MA_CROSS})
        self.assertEqual(dl.call_count, n)  # 第二次全部走快取
        self.assertTrue(PriceCache.objects.filter(symbol="2330.TW").exists())

    def test_stale_cache_used_when_download_fails(self, dl):
        self.post({"symbol": "2330", "strategy": MA_CROSS})
        PriceCache.objects.update(updated_at=timezone.now() - timedelta(days=2))
        dl.side_effect = RuntimeError("yahoo down")
        d = self.post({"symbol": "2330", "strategy": MA_CROSS}).json()
        self.assertTrue(d["ok"])
        self.assertTrue(any("快取" in n for n in d["notes"]))

    def test_invalid_strategy_400_with_message(self, _dl):
        bad = json.loads(json.dumps(MA_CROSS))
        bad["entry"]["conditions"][0]["left"]["name"] = "os.system"
        r = self.post({"symbol": "2330", "strategy": bad})
        self.assertEqual(r.status_code, 400)
        self.assertIn("不支援的指標", r.json()["error"])

    def test_missing_symbol_and_short_range(self, _dl):
        r = self.post({"symbol": "", "strategy": MA_CROSS})
        self.assertEqual(r.status_code, 400)
        r = self.post({"symbol": "2330", "start": "2024-01-01", "end": "2024-01-15", "strategy": MA_CROSS})
        self.assertEqual(r.status_code, 400)
        self.assertIn("2 個月", r.json()["error"])

    def test_bad_json_and_settings(self, _dl):
        r = self.c.post("/backtest/api/run", data="{not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        r = self.post({"symbol": "2330", "strategy": MA_CROSS, "settings": {"capital": -5}})
        self.assertEqual(r.status_code, 400)
        self.assertIn("初始資金", r.json()["error"])

    def test_csrf_enforced(self, _dl):
        c = Client(enforce_csrf_checks=True)
        r = self.post({"symbol": "2330", "strategy": MA_CROSS}, client=c)
        self.assertEqual(r.status_code, 403)

    def test_get_not_allowed_on_run(self, _dl):
        self.assertEqual(self.c.get("/backtest/api/run").status_code, 405)

    def test_rate_limit(self, _dl):
        with mock.patch.object(views, "RATE_LIMIT", 2):
            codes = [self.post({"symbol": "2330", "strategy": MA_CROSS}).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_unknown_stock_502(self, dl):
        dl.side_effect = lambda s: pd.DataFrame()
        r = self.post({"symbol": "9999", "strategy": MA_CROSS})
        self.assertEqual(r.status_code, 502)
        self.assertIn("抓不到", r.json()["error"])

    def test_unknown_code_negative_cached(self, dl):
        dl.side_effect = lambda s: pd.DataFrame()
        self.post({"symbol": "9999", "strategy": MA_CROSS})
        n = dl.call_count
        r = self.post({"symbol": "9999", "strategy": MA_CROSS})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(dl.call_count, n)  # 第二次不再打 Yahoo

    def test_client_ip_uses_proxy_appended_value(self, _dl):
        from django.test import RequestFactory
        rf = RequestFactory()
        req = rf.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 1.2.3.4", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(views._client_ip(req), "1.2.3.4")
        # 不是從本機代理來的請求，不信任 XFF
        req = rf.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6", REMOTE_ADDR="8.8.8.8")
        self.assertEqual(views._client_ip(req), "8.8.8.8")

    def test_unfinished_intraday_bar_dropped(self, _dl):
        import datetime as dt
        from zoneinfo import ZoneInfo
        df = fake_df(n=50)
        tw = ZoneInfo("Asia/Taipei")
        last = df.index[-1]
        during = dt.datetime(last.year, last.month, last.day, 10, 0, tzinfo=tw)
        after = dt.datetime(last.year, last.month, last.day, 15, 0, tzinfo=tw)
        self.assertEqual(len(prices._drop_unfinished_bar(df, during)), 49)
        self.assertEqual(len(prices._drop_unfinished_bar(df, after)), 50)

    def test_etf_detected(self, _dl):
        d = self.post({"symbol": "0050", "strategy": MA_CROSS}).json()
        self.assertTrue(d["stock"]["is_etf"])
