"""資料模型 — 見 .knowledge/specs/data-model.md。"""
from django.db import models


class WatchTarget(models.Model):
    """追蹤標的設定。"""

    symbol = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=32)
    asset_class = models.CharField(max_length=16)  # tw_stock / us_index / gold / forex
    market = models.CharField(max_length=8, db_index=True)  # tw / us
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.display_name} ({self.symbol})"


class SignalLog(models.Model):
    """訊號紀錄 — 供防抖動去重與稽核。"""

    target = models.ForeignKey(
        WatchTarget, on_delete=models.CASCADE, related_name="signals"
    )
    indicator = models.CharField(max_length=16)  # ma / macd / rsi / kd / bollinger
    direction = models.CharField(max_length=8)  # bullish / bearish
    trigger_date = models.DateField()
    triggered_at = models.DateTimeField()
    detail = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["target", "indicator", "direction", "triggered_at"],
                name="idx_signal_dedup",
            )
        ]

    def __str__(self):
        return f"{self.target_id}:{self.indicator}:{self.direction}@{self.trigger_date}"


class PushLog(models.Model):
    """推播紀錄。"""

    channel = models.CharField(max_length=16, default="line")  # line / discord
    market = models.CharField(max_length=8)
    push_mode = models.CharField(max_length=16)  # broadcast / targets / webhook / dry_run
    message = models.TextField()
    signal_count = models.IntegerField(default=0)
    status = models.CharField(max_length=16)  # success / failed / dry_run
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.market}:{self.status}@{self.created_at:%Y-%m-%d %H:%M}"
