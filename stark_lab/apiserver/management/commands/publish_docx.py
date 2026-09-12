# -*- coding: utf-8 -*-
"""把 Word (.docx) 轉成部落格文章並上站（單篇）。

用法：
    python manage.py publish_docx "C:\\path\\週報.docx"
    python manage.py publish_docx 檔案.docx --cat 2 --title "我的標題" --date 2026-09-12

參數：
    docx            Word 檔路徑（必填，僅支援 .docx）
    --cat 1|2       1=產業時事分析(article_1)  2=科技分享(article_2)，預設 1
    --title         標題（不填則自動抓 Word 第一個標題，再不行用檔名）
    --author        作者名，預設「史塔克實驗室」
    --author-pic    作者頭像 URL（選填）
    --cover         封面圖 URL（不填則用文內第一張圖）
    --abstract      摘要（不填則自動抓第一段文字）
    --date          日期字串（不填則用今天）
    --link          原文連結（選填；僅作「原文出處」顯示，canonical 仍在主站）
    --update ID     傳既有文章 id 則覆蓋更新該篇

輸出：成功後印出文章網址，例如 https://starklab.tw/blog/12/
"""
import os

from django.core.management.base import BaseCommand, CommandError

from apiserver.blogimport import docx_to_fields, save_article, blog_path


class Command(BaseCommand):
    help = "把 Word (.docx) 轉成部落格文章並上站"

    def add_arguments(self, parser):
        parser.add_argument('docx', help='Word 檔路徑 (.docx)')
        parser.add_argument('--cat', type=int, default=1, choices=[1, 2])
        parser.add_argument('--title', default='')
        parser.add_argument('--author', default='史塔克實驗室')
        parser.add_argument('--author-pic', dest='author_pic', default='')
        parser.add_argument('--cover', default='')
        parser.add_argument('--abstract', default='')
        parser.add_argument('--date', default='')
        parser.add_argument('--link', default='')
        parser.add_argument('--update', type=int, default=0)

    def handle(self, *args, **opts):
        try:
            import mammoth  # noqa: F401
        except ImportError:
            raise CommandError("缺少 mammoth 套件，請先執行： pip install mammoth")

        docx_path = os.path.abspath(opts['docx'])
        if not os.path.isfile(docx_path):
            raise CommandError("找不到檔案: %s" % docx_path)
        if not docx_path.lower().endswith('.docx'):
            raise CommandError("只支援 .docx（不支援舊版 .doc，請先另存為 .docx）")

        cat = int(opts['cat'])
        fields, n_img, messages = docx_to_fields(
            docx_path,
            title=opts['title'], author=opts['author'], author_pic=opts['author_pic'],
            cover=opts['cover'], abstract=opts['abstract'], date=opts['date'], link=opts['link'],
        )
        for m in messages:
            self.stdout.write("  [mammoth] %s" % m)

        obj, action = save_article(cat, fields, update_id=opts['update'])
        path = blog_path(cat, obj.id)
        self.stdout.write(self.style.SUCCESS(
            "\n[OK] %s成功！\n  標題：%s\n  分類：%s\n  圖片：%d 張\n  網址：https://starklab.tw%s\n"
            % (action, fields['title'], "產業時事分析" if cat == 1 else "科技分享", n_img, path)
        ))
