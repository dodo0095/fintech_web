"""即時抓取並寫入 DB（排程呼叫此指令，對應原 news_platform/scripts/run_all.py）。

用法：
    python manage.py update_news                 # 全部來源
    python manage.py update_news --only market news   # 只跑指定來源

容錯：單一來源失敗不影響其他，且失敗來源「不覆寫」DB 既有資料；
最後寫入 status 心跳（各來源成敗、最後執行時間），供前端排程心跳顯示。
"""
from django.core.management.base import BaseCommand

from news import store
from news.fetchers import (
    market as f_market,
    headlines as f_headlines,
    tsmc as f_tsmc,
    fed as f_fed,
    events as f_events,
    valuation as f_valuation,
    heat as f_heat,
    summary as f_summary,
)
from news.fetchers.common import now_iso

# key -> (status 用的 script 名稱)，順序即執行順序；
# heat / summary 需在 market/valuation 之後（讀其他 payload 合成）
ORDER = ["market", "headlines", "tsmc", "fed", "valuation", "events", "heat", "summary"]
SCRIPT_NAME = {
    "market": "fetch_market.py",
    "headlines": "fetch_news.py",
    "tsmc": "fetch_tsmc_news.py",
    "fed": "fetch_fed.py",
    "valuation": "fetch_valuation.py",
    "events": "fetch_events.py",
    "heat": "fetch_heat.py",
    "summary": "fetch_summary.py",
}


class Command(BaseCommand):
    help = "即時抓取市場/新聞/估值等資料並寫入 DB"

    def add_arguments(self, parser):
        parser.add_argument("--only", nargs="+", choices=ORDER, default=None,
                            help="只跑指定來源（預設全跑）")

    def handle(self, *args, **opts):
        only = opts["only"]
        selected = [k for k in ORDER if (only is None or k in only)]
        results = {}          # key -> bool
        payloads = {}         # key -> payload（供 heat 使用）

        for key in selected:
            self.stdout.write("--- {} ---".format(SCRIPT_NAME[key]))
            try:
                if key == "market":
                    p = f_market.build(); store.store_market(p); payloads["market"] = p
                elif key == "headlines":
                    p = f_headlines.build(); store.store_headlines(p); payloads["headlines"] = p
                elif key == "tsmc":
                    p = f_tsmc.build(); store.store_tsmc(p); payloads["tsmc"] = p
                elif key == "fed":
                    p = f_fed.build(); store.store_fed(p); payloads["fed"] = p
                elif key == "events":
                    p = f_events.build(); store.store_events(p)
                elif key == "valuation":
                    bundle = f_valuation.build()
                    for code, vp in bundle["symbols"].items():
                        store.store_valuation(code, vp)
                    store.set_default_valuation(bundle["default_code"])
                    store.store_watchlist(bundle["watchlist"])
                    payloads["valuation_default"] = bundle["symbols"].get(bundle["default_code"])
                elif key == "heat":
                    prev = store.read_heat()
                    p = f_heat.build(
                        news=payloads.get("headlines") or store.read_headlines(),
                        tsmc=payloads.get("tsmc") or store.read_tsmc(),
                        fed=payloads.get("fed") or store.read_fed(),
                        prev=prev,
                        name_code="2330",
                        name_name="台積電",
                    )
                    store.store_heat(p)
                    payloads["heat"] = p
                elif key == "summary":
                    p = f_summary.build(
                        market=payloads.get("market") or store.read_market(),
                        heat=payloads.get("heat") or store.read_heat(),
                        valuation=payloads.get("valuation_default") or store.read_valuation(),
                    )
                    store.store_summary(p)
                results[key] = True
                self.stdout.write(self.style.SUCCESS("  [ok] {}".format(key)))
            except Exception as e:
                results[key] = False
                self.stderr.write("  [warn] {} 失敗，保留既有資料：{}".format(key, e))

        ok_count = sum(1 for v in results.values() if v)
        total = len(results)
        status_payload = {
            "ran_at": now_iso(),
            "ok": ok_count == total and total > 0,
            "ok_count": ok_count,
            "total": total,
            "sources": [{"script": SCRIPT_NAME[k], "ok": results[k]} for k in selected],
        }
        store.store_status(status_payload)

        self.stdout.write("=== done: {}/{} ok ===".format(ok_count, total))
        # 至少一個成功即視為整體成功（排程不因單一來源失敗而每次告警）
        return None
