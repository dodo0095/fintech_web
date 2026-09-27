"""sitemap.xml：主要公開靜態頁 + 所有有站內正文的部落格文章。

不使用 django.contrib.sites（避免正式機多跑一次 migrate），
改由 settings.SITE_BASE_URL 決定輸出的協定與網域，
因此不論請求來自 127.0.0.1 或反向代理，sitemap 內一律是正式網址。
"""
from types import SimpleNamespace
from urllib.parse import urlsplit

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apiserver.models import article_1, article_2
from apiserver.seo import article_modified_at, site_base_url

PUBLIC_STATIC_PAGES = (
    "/",
    "/botBlog.html",
    "/bot.html",
    "/botAbout.html",
    "/botBasicCurrent.html",
    "/botBasicHistory.html",
    "/botTechnicCurrent.html",
    "/botTechnicHistory.html",
)


class CanonicalSiteSitemap(Sitemap):
    """忽略請求的 Host，固定以 SITE_BASE_URL 的協定與網域輸出 <loc>。"""

    def get_urls(self, page=1, site=None, protocol=None):
        base = urlsplit(site_base_url())
        canonical_site = SimpleNamespace(domain=base.netloc, name=base.netloc)
        return super().get_urls(page=page, site=canonical_site, protocol=base.scheme)


class StaticPagesSitemap(CanonicalSiteSitemap):
    changefreq = "weekly"

    def items(self):
        return list(PUBLIC_STATIC_PAGES)

    def location(self, item):
        return item


class ArticleSitemap(CanonicalSiteSitemap):
    """content 為空（或只有空白）的舊文會被 article_detail 導去外站，不列入。"""

    changefreq = "monthly"
    model = None
    url_name = ""

    def items(self):
        return (
            self.model.objects.exclude(content__regex=r"^\s*$")
            .defer("content")
            .order_by("-id")
        )

    def location(self, article):
        return reverse(self.url_name, kwargs={"pk": article.pk})

    def lastmod(self, article):
        return article_modified_at(article)


class IndustryArticleSitemap(ArticleSitemap):
    model = article_1
    url_name = "article_detail"


class TechArticleSitemap(ArticleSitemap):
    model = article_2
    url_name = "article_detail_tech"


SITEMAPS = {
    "static": StaticPagesSitemap,
    "industry": IndustryArticleSitemap,
    "tech": TechArticleSitemap,
}
