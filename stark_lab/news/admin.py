from django.contrib import admin

from news.models import Snapshot, NewsItem, MarketEvent, WatchlistItem, Valuation


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("kind", "fetched_at")
    search_fields = ("kind",)


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ("category", "rank", "title", "source", "stance", "time")
    list_filter = ("category", "source")
    search_fields = ("title", "summary")


@admin.register(MarketEvent)
class MarketEventAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "actual", "forecast", "previous", "visible")
    list_filter = ("visible",)


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("position", "code", "symbol", "name")


@admin.register(Valuation)
class ValuationAdmin(admin.ModelAdmin):
    list_display = ("code", "updated_at")
