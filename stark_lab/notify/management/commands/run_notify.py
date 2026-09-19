"""排程進入點（單次執行一個市場）。

用法：
    python manage.py run_notify --market tw
    python manage.py run_notify --market us

核心流程在 notify/runner.py（與 run_scheduler 共用）。
"""
from django.core.management.base import BaseCommand

from notify import runner


class Command(BaseCommand):
    help = "抓取日線、計算指標、推播觸發訊號（單次）"

    def add_arguments(self, parser):
        parser.add_argument("--market", required=True, choices=["tw", "us"])

    def handle(self, *args, **options):
        summary = runner.run_market(options["market"])
        self.stdout.write(summary)
