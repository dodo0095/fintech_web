from django.test import SimpleTestCase, TestCase

from news.heat_v1 import decide_trend, headline_heat, map_gauge, score_titles
from news.tickers import lookup


class HeatV1Tests(SimpleTestCase):
    def test_longest_match_drops_short_tariff(self):
        heat, off, on = headline_heat("美國取消關稅後台股反彈")
        self.assertNotIn("關稅", off)
        self.assertTrue("取消關稅" in on or heat <= 0)

    def test_war_not_warning(self):
        heat, off, on = headline_heat("Fed warning on inflation outlook")
        self.assertNotIn("war", off)
        self.assertEqual(heat, 0)

    def test_commentary_zero(self):
        heat, off, on = headline_heat("一文看懂關稅有哪些多重風險")
        self.assertEqual(heat, 0)
        self.assertEqual(off, [])

    def test_taco_cools_generic_tariff(self):
        heat, off, on = headline_heat("川普又TACO 加拿大關稅生效前踩剎車")
        self.assertLessEqual(heat, 0)
        self.assertNotIn("關稅", off)

    def test_score_dedup(self):
        scored = score_titles([
            "關稅衝擊台積電 - 鉅亨網",
            "關稅衝擊台積電 - Yahoo股市",
        ])
        self.assertEqual(scored["n_unique"], 1)

    def test_gauge_severe_not_capped_same(self):
        a, la = map_gauge(12, "severe")
        b, lb = map_gauge(36, "severe")
        self.assertEqual(la, "嚴重")
        self.assertEqual(lb, "嚴重")
        self.assertGreater(b, a)
        self.assertLessEqual(b, 100)

    def test_trend_cooling(self):
        trend, _ = decide_trend(8, 12)
        self.assertEqual(trend, "cooling")


class TickerLookupTests(SimpleTestCase):
    def test_tsmc(self):
        info = lookup("2330")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "台積電")
        self.assertTrue(info["yahoo"].endswith(".TW"))

    def test_name(self):
        info = lookup("台積電")
        self.assertIsNotNone(info)
        self.assertEqual(info["code"], "2330")

    def test_unknown(self):
        self.assertIsNone(lookup("ZZZZZ"))

    def test_code_only_strips_suffix(self):
        a = lookup("2317")
        b = lookup("2317.TW")
        c = lookup("2317.TWO")
        self.assertEqual(a["code"], "2317")
        self.assertEqual(b["code"], "2317")
        self.assertEqual(c["code"], "2317")
        self.assertEqual(a["name"], "鴻海")

    def test_yahoo_try_tw_then_two(self):
        from news.tickers import yahoo_candidates
        listed = yahoo_candidates({"code": "2330", "yahoo": "2330.TW"})
        self.assertEqual(listed[0], "2330.TW")
        self.assertEqual(listed[1], "2330.TWO")
        otc = yahoo_candidates({"code": "5483", "yahoo": "5483.TWO"})
        self.assertEqual(otc[0], "5483.TWO")
        self.assertEqual(otc[1], "5483.TW")


class NewsApiTests(TestCase):
    def test_unknown_stock_404(self):
        r = self.client.get("/api/news/stock/ZZZZZ")
        self.assertEqual(r.status_code, 404)

    def test_unknown_valuation_404(self):
        r = self.client.get("/api/news/valuation/ZZZZZ")
        self.assertEqual(r.status_code, 404)

    def test_heat_unknown_code_404(self):
        r = self.client.get("/api/news/heat", {"code": "ZZZZZ"})
        self.assertEqual(r.status_code, 404)
