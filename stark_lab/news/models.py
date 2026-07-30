"""news app 資料模型。

設計原則（見 docs/decisions/news-platform-integration.md）：
- 能查詢的實體資料用關聯式 row 模型：NewsItem / MarketEvent / WatchlistItem
- 文件型 / 計算後 blob 用 JSONField 整包存：Valuation（河流圖）、Snapshot（市場/熱度/狀態/各 feed meta）
- 時間欄位一律以「原始 ISO 字串」保存，確保 DRF 輸出與原 data/*.json 逐欄位一致

Django 3.0 無原生 JSONField，統一使用第三方 jsonfield.JSONField（對齊正式機）。
"""
from django.db import models
from jsonfield import JSONField


class Snapshot(models.Model):
    """document 型 / 單例快照的 KV 儲存，以 kind 區分。

    kind 一覽：
      market          -> 完整 market.json
      heat            -> 完整 heat.json
      status          -> 完整 status.json
      headlines_meta  -> {"updated_at": ...}
      tsmc_meta       -> {"updated_at":..., "symbol":..., "name":...}
      fed_meta        -> {"updated_at": ...}
      events_meta     -> {"updated_at": ...}
      watchlist_meta  -> {"updated_at": ...}
    """
    kind = models.CharField(max_length=32, unique=True, db_index=True)
    payload = JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "快照 (Snapshot)"
        verbose_name_plural = "快照 (Snapshot)"

    def __str__(self):
        return self.kind


class NewsItem(models.Model):
    """新聞條目：頭條 / 台積電專區 / 聯準會，以 category 區分。"""
    CATEGORY_HEADLINE = "headline"
    CATEGORY_TSMC = "tsmc"
    CATEGORY_FED = "fed"
    CATEGORY_CHOICES = (
        (CATEGORY_HEADLINE, "頭條"),
        (CATEGORY_TSMC, "台積電"),
        (CATEGORY_FED, "聯準會"),
    )

    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, db_index=True)
    rank = models.IntegerField(default=0)
    title = models.TextField()
    summary = models.TextField(blank=True)
    source = models.CharField(max_length=120, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    time = models.CharField(max_length=40, blank=True)  # 原始 ISO 字串
    tags = JSONField(default=list, blank=True)          # 僅頭條有
    stance = models.CharField(max_length=16, blank=True, null=True)  # 僅 fed：hawk / dove / neutral

    class Meta:
        ordering = ["category", "rank"]
        verbose_name = "新聞條目"
        verbose_name_plural = "新聞條目"

    def __str__(self):
        return "[{}] {}".format(self.category, self.title[:30])


class MarketEvent(models.Model):
    """關注事件（非農等）。"""
    name = models.CharField(max_length=80)
    date = models.CharField(max_length=20)  # 原始 YYYY-MM-DD 字串
    actual = models.FloatField(null=True, blank=True)
    forecast = models.FloatField(null=True, blank=True)
    previous = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "關注事件"
        verbose_name_plural = "關注事件"

    def __str__(self):
        return "{} {}".format(self.date, self.name)


class WatchlistItem(models.Model):
    """河流圖觀察名單。"""
    code = models.CharField(max_length=12, unique=True)
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=40)
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ["position"]
        verbose_name = "觀察名單"
        verbose_name_plural = "觀察名單"

    def __str__(self):
        return "{} {}".format(self.code, self.name)


class Valuation(models.Model):
    """本益比 / 淨值比河流圖：每檔一份計算後圖表快照（整包 JSON）。"""
    code = models.CharField(max_length=12, unique=True, db_index=True)
    updated_at = models.CharField(max_length=40, blank=True)
    payload = JSONField(default=dict)  # 完整 valuation_{code}.json

    class Meta:
        verbose_name = "估值河流圖"
        verbose_name_plural = "估值河流圖"

    def __str__(self):
        return self.code
