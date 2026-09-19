"""notify 測試共用設定。

以 pytest-django 執行；預設用 stark_lab.settings。多數 run_notify / dashboard
測試需要 Discord 通報線啟用且乾跑（不打網路），故以 autouse fixture 統一預設，
個別測試仍可自行覆寫 settings。
"""
import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stark_lab.settings")


@pytest.fixture(autouse=True)
def _notify_defaults(settings):
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = True
