from django.contrib import admin

from .models import PriceCache


@admin.register(PriceCache)
class PriceCacheAdmin(admin.ModelAdmin):
    list_display = ("symbol", "first_date", "last_date", "rows", "updated_at")
    search_fields = ("symbol",)
    exclude = ("payload",)
