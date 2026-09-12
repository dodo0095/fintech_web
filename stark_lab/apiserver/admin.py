from django.contrib import admin
from apiserver.models import article_1, article_2


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
