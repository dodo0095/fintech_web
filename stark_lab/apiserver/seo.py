"""SEO 共用工具：站台絕對網址、文章日期解析。

文章的 date / updated 欄位是自由輸入的 TextField，格式不保證正確，
因此這裡所有解析都「失敗回 None」，由呼叫端決定要不要省略該欄位，
不可讓 sitemap 或文章頁因為單篇髒資料而 500。
"""
import datetime

from django.conf import settings
from django.utils import timezone

ARTICLE_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
)


def site_base_url():
    """對外正式網址（不含結尾斜線），例如 https://starklab.tw。"""
    return settings.SITE_BASE_URL.rstrip("/")


def absolute_site_url(path_or_url):
    """把站內路徑補成絕對網址；已是絕對網址者原樣回傳。空值回空字串。"""
    value = (path_or_url or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("//"):
        return "https:" + value
    if not value.startswith("/"):
        value = "/" + value
    return site_base_url() + value


def parse_article_datetime(text):
    """解析文章的 date / updated 字串為台北時區 aware datetime；無法解析回 None。"""
    value = (text or "").strip()
    if not value:
        return None
    for fmt in ARTICLE_DATETIME_FORMATS:
        try:
            naive = datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
        return timezone.make_aware(naive, timezone.get_default_timezone())
    return None


def article_published_at(article):
    return parse_article_datetime(article.date)


def article_modified_at(article):
    """最後修改時間：updated 可解析就用 updated，否則退回發佈日期（皆失敗回 None）。"""
    return parse_article_datetime(article.updated) or article_published_at(article)
