import json
import re

from django.test import TestCase, override_settings

from apiserver.models import article_1, article_2
from apiserver.seo import absolute_site_url, parse_article_datetime

SITE = "https://starklab.tw"


def make_article(model=article_1, **overrides):
    fields = dict(
        title="測試文章",
        title_picture="",
        abstract="摘要",
        author_name="史塔克實驗室",
        date="2026-09-27",
        link="",
        content="<p>正文</p>",
        updated="",
    )
    fields.update(overrides)
    return model.objects.create(**fields)


def extract_json_ld(html):
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return json.loads(match.group(1))


@override_settings(SITE_BASE_URL=SITE)
class SitemapTests(TestCase):
    def test_sitemap_lists_articles_with_content_on_canonical_domain(self):
        industry = make_article(article_1)
        tech = make_article(article_2)
        legacy = make_article(article_1, content="", link="https://vocus.cc/old")
        blank = make_article(article_1, content="   \n ", link="https://vocus.cc/blank")

        response = self.client.get("/sitemap.xml", HTTP_HOST="127.0.0.1")
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn(f"<loc>{SITE}/blog/{industry.pk}/</loc>", body)
        self.assertIn(f"<loc>{SITE}/blog/tech/{tech.pk}/</loc>", body)
        self.assertNotIn(f"/blog/{legacy.pk}/</loc>", body)
        self.assertNotIn(f"/blog/{blank.pk}/</loc>", body)
        self.assertNotIn("127.0.0.1", body)
        locations = re.findall(r"<loc>(.*?)</loc>", body)
        self.assertTrue(locations)
        for location in locations:
            self.assertTrue(location.startswith(f"{SITE}/"), location)

    def test_sitemap_includes_public_static_pages_only(self):
        body = self.client.get("/sitemap.xml").content.decode()

        for page in ("/", "/botBlog.html", "/bot.html", "/botAbout.html"):
            self.assertIn(f"<loc>{SITE}{page}</loc>", body)
        for hidden in ("news.html", "/_ops/", "/backtest/", "/api/"):
            self.assertNotIn(hidden, body)

    def test_lastmod_prefers_updated_then_date(self):
        with_updated = make_article(date="2026-09-01", updated="2026-09-20 10:30")
        date_only = make_article(date="2026-08-15", updated="")

        body = self.client.get("/sitemap.xml").content.decode()

        self.assertIn(
            f"<loc>{SITE}/blog/{with_updated.pk}/</loc><lastmod>2026-09-20</lastmod>", body
        )
        self.assertIn(
            f"<loc>{SITE}/blog/{date_only.pk}/</loc><lastmod>2026-08-15</lastmod>", body
        )

    def test_malformed_dates_do_not_break_sitemap(self):
        bad = make_article(date="不明日期", updated="yesterday-ish")
        fallback = make_article(date="2026-07-01", updated="2026/13/45 99:99")

        response = self.client.get("/sitemap.xml")
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertRegex(body, rf"<loc>{SITE}/blog/{bad.pk}/</loc>\s*<changefreq>")
        self.assertIn(
            f"<loc>{SITE}/blog/{fallback.pk}/</loc><lastmod>2026-07-01</lastmod>", body
        )


class RobotsTxtTests(TestCase):
    def test_robots_txt_declares_sitemap_and_keeps_ops_disallow(self):
        response = self.client.get("/robots.txt")
        lines = response.content.decode().splitlines()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Sitemap: https://starklab.tw/sitemap.xml", lines)
        self.assertIn("Disallow: /_ops/", lines)


@override_settings(SITE_BASE_URL=SITE)
class ArticleDetailSeoTests(TestCase):
    def get_html(self, article, prefix="/blog/"):
        response = self.client.get(f"{prefix}{article.pk}/")
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_relative_title_picture_becomes_absolute_og_image(self):
        article = make_article(title_picture="/media/blog/20260927/img1.png")

        html = self.get_html(article)

        expected = f"{SITE}/media/blog/20260927/img1.png"
        self.assertIn(f'<meta property="og:image" content="{expected}">', html)
        self.assertEqual(extract_json_ld(html)["image"], expected)

    def test_absolute_title_picture_is_kept(self):
        url = "https://images.example.com/cover.jpg"
        article = make_article(article_2, title_picture=url)

        html = self.get_html(article, prefix="/blog/tech/")

        self.assertIn(f'<meta property="og:image" content="{url}">', html)
        self.assertEqual(extract_json_ld(html)["image"], url)

    def test_no_title_picture_omits_og_image(self):
        html = self.get_html(make_article(title_picture=""))

        self.assertNotIn('property="og:image"', html)
        self.assertNotIn("image", extract_json_ld(html))

    def test_json_ld_dates_are_iso8601_with_taipei_offset(self):
        article = make_article(date="2026-09-27", updated="2026-09-28 14:05")

        data = extract_json_ld(self.get_html(article))

        self.assertEqual(data["datePublished"], "2026-09-27T00:00:00+08:00")
        self.assertEqual(data["dateModified"], "2026-09-28T14:05:00+08:00")

    def test_date_modified_falls_back_to_published(self):
        article = make_article(date="2026-09-27", updated="")

        data = extract_json_ld(self.get_html(article))

        self.assertEqual(data["dateModified"], data["datePublished"])

    def test_malformed_dates_are_omitted_not_500(self):
        article = make_article(date="not-a-date", updated="also bad")

        data = extract_json_ld(self.get_html(article))

        self.assertNotIn("datePublished", data)
        self.assertNotIn("dateModified", data)

    def test_favicon_uses_absolute_path(self):
        html = self.get_html(make_article())

        self.assertIn('<link href="/static/images/favicon.ico" rel="shortcut icon">', html)


@override_settings(SITE_BASE_URL=SITE)
class SeoHelperTests(TestCase):
    def test_absolute_site_url(self):
        self.assertEqual(absolute_site_url("/media/a.png"), f"{SITE}/media/a.png")
        self.assertEqual(absolute_site_url("media/a.png"), f"{SITE}/media/a.png")
        self.assertEqual(absolute_site_url("//cdn.example.com/a.png"), "https://cdn.example.com/a.png")
        self.assertEqual(absolute_site_url("http://x.tw/a.png"), "http://x.tw/a.png")
        self.assertEqual(absolute_site_url(""), "")

    def test_parse_article_datetime_handles_bad_input(self):
        self.assertIsNone(parse_article_datetime(""))
        self.assertIsNone(parse_article_datetime(None))
        self.assertIsNone(parse_article_datetime("2026-02-30"))
        self.assertEqual(
            parse_article_datetime("2026-09-27 08:30").isoformat(), "2026-09-27T08:30:00+08:00"
        )
