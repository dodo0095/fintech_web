"""從既有 news_platform/data/*.json 種子匯入 DB（一次性 bootstrap / demo 用）。

用法：
    python manage.py import_news_json
    python manage.py import_news_json --data-dir "C:/path/to/news_platform/data"

即時更新請改用 update_news；本指令僅為初始化既有真實資料。
"""
import json
import os

from django.core.management.base import BaseCommand

from news import store

DEFAULT_DATA_DIR = r"C:\Users\Bandai\Desktop\Dream_project\news_platform\data"


class Command(BaseCommand):
    help = "從 news_platform/data/*.json 種子匯入 news app 資料庫"

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    def _load(self, data_dir, name):
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def handle(self, *args, **opts):
        data_dir = opts["data_dir"]
        if not os.path.isdir(data_dir):
            self.stderr.write("找不到 data 目錄：{}".format(data_dir))
            return

        done = []

        simple = [
            ("market.json", store.store_market),
            ("news.json", store.store_headlines),
            ("tsmc_news.json", store.store_tsmc),
            ("fed.json", store.store_fed),
            ("heat.json", store.store_heat),
            ("events.json", store.store_events),
            ("watchlist.json", store.store_watchlist),
            ("summary.json", store.store_summary),
            ("status.json", store.store_status),
        ]
        for name, fn in simple:
            payload = self._load(data_dir, name)
            if payload is not None:
                fn(payload)
                done.append(name)

        # 估值：valuation_{code}.json 逐檔 + 預設
        default_code = None
        for fname in sorted(os.listdir(data_dir)):
            if fname.startswith("valuation_") and fname.endswith(".json"):
                code = fname[len("valuation_"):-len(".json")]
                payload = self._load(data_dir, fname)
                if payload:
                    store.store_valuation(code, payload)
                    done.append(fname)
        # 預設 valuation.json → 取其 symbol 對應 code；否則觀察名單首檔或 2330
        default_payload = self._load(data_dir, "valuation.json")
        if default_payload and default_payload.get("symbol"):
            default_code = str(default_payload["symbol"]).split(".")[0]
        if not default_code:
            wl = self._load(data_dir, "watchlist.json") or {}
            items = wl.get("items") or []
            default_code = items[0]["code"] if items else "2330"
        store.set_default_valuation(default_code)
        done.append("valuation(default={})".format(default_code))

        self.stdout.write(self.style.SUCCESS(
            "種子匯入完成（{} 項）：{}".format(len(done), ", ".join(done))
        ))
