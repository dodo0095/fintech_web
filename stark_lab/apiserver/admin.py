import csv
from django.contrib import admin
from django.http import HttpResponse
from apiserver.models import article_1, article_2, Subscriber


class ArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author_name", "date", "has_content")
    search_fields = ("title", "abstract", "author_name")
    ordering = ("-id",)

    def has_content(self, obj):
        return bool((obj.content or "").strip())
    has_content.boolean = True
    has_content.short_description = "站內正文"


admin.site.register(article_1, ArticleAdmin)
admin.site.register(article_2, ArticleAdmin)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created")
    search_fields = ("email",)
    list_filter = ("source",)
    ordering = ("-created",)
    actions = ["export_csv"]

    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=subscribers.csv"
        resp.write("﻿")  # BOM，讓 Excel 正確顯示中文
        writer = csv.writer(resp)
        writer.writerow(["email", "source", "created"])
        for s in queryset:
            writer.writerow([s.email, s.source, s.created.strftime("%Y-%m-%d %H:%M")])
        return resp
    export_csv.short_description = "匯出所選為 CSV"
