# -*- coding: utf-8 -*-
"""批次回填台股週報：把 finanical_Column/articles/*/ 的週報 Word 一次上站。

會讀每週資料夾的 config.yaml 取 title / subtitle / publish_date：
  - 文章標題 = subtitle（較有吸引力的那句）> title > docx 第一標題
  - 日期     = publish_date
以檔名（source_docx）做冪等，重複執行不會建立重複文章（除非 --force）。

用法：
    python manage.py backfill_weekly --dir "C:\\...\\finanical_Column\\articles"
    python manage.py backfill_weekly --dry-run          # 只列出不寫入
    python manage.py backfill_weekly --force            # 已存在也重新建立
"""
import os
import re
import glob
import datetime

from django.core.management.base import BaseCommand, CommandError

from apiserver.models import article_1
from apiserver.blogimport import docx_to_fields, save_article, blog_path


DEFAULT_PATTERN = "*台股週報_方格子專欄.docx"


def _md_h1(folder):
    """取資料夾內 weekly-report*.md 的第一個 H1 當標題（vocus 版優先，標題較吸引人）。"""
    mds = glob.glob(os.path.join(folder, 'weekly-report*.md'))
    mds.sort(key=lambda p: (0 if 'vocus' in os.path.basename(p).lower() else 1, p))
    for md in mds:
        try:
            with open(md, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('# '):
                        return line[2:].strip()
        except Exception:
            continue
    return ''


def _week_from_folder(folder):
    """從資料夾名 2026-W14 取 (year, week)。"""
    m = re.search(r'(\d{4})-W(\d{1,2})', os.path.basename(folder))
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _iso_friday(year, week):
    """該 ISO 週的週五當發佈日。"""
    try:
        return datetime.date.fromisocalendar(year, week, 5).strftime('%Y-%m-%d')
    except Exception:
        return ''


class Command(BaseCommand):
    help = "批次把台股週報 Word 回填到主站部落格（article_1）"

    def add_arguments(self, parser):
        parser.add_argument('--dir', dest='base_dir', default='',
                            help='週報 articles 根目錄；預設推導 ../../finanical_Column/articles')
        parser.add_argument('--dry-run', action='store_true', help='只列出，不寫入')
        parser.add_argument('--force', action='store_true', help='已存在同檔名也重新建立')

    def _default_dir(self):
        from django.conf import settings
        base = str(settings.BASE_DIR)  # stark_lab
        cand = os.path.abspath(os.path.join(base, '..', '..', 'finanical_Column', 'articles'))
        return cand

    def handle(self, *args, **opts):
        try:
            import mammoth  # noqa: F401
        except ImportError:
            raise CommandError("缺少 mammoth 套件，請先執行： pip install mammoth")
        try:
            import yaml
        except ImportError:
            yaml = None
            self.stdout.write(self.style.WARNING("未安裝 PyYAML，將改用 docx 第一標題/檔名當標題"))

        base_dir = opts['base_dir'] or self._default_dir()
        if not os.path.isdir(base_dir):
            raise CommandError("找不到週報目錄: %s（請用 --dir 指定）" % base_dir)

        docx_paths = sorted(
            p for p in glob.glob(os.path.join(base_dir, '*', DEFAULT_PATTERN))
            if not os.path.basename(p).startswith('~')
        )
        if not docx_paths:
            raise CommandError("在 %s 找不到週報 Word（%s）" % (base_dir, DEFAULT_PATTERN))

        self.stdout.write("找到 %d 篇週報 Word\n" % len(docx_paths))

        created, skipped, failed = 0, 0, 0
        for path in docx_paths:
            fname = os.path.basename(path)
            folder = os.path.dirname(path)

            # 冪等：同檔名已上過就跳過
            if not opts['force'] and article_1.objects.filter(source_docx=fname).exists():
                self.stdout.write("  [skip] 已存在：%s" % fname)
                skipped += 1
                continue

            # 標題/日期來源鏈：config.yaml → weekly-report*.md 的 H1 → 由週次生成
            title = date = abstract = ''
            cfg_path = os.path.join(folder, 'config.yaml')
            if yaml and os.path.isfile(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = yaml.safe_load(f) or {}
                    title = (cfg.get('subtitle') or cfg.get('title') or '').strip()
                    date = str(cfg.get('publish_date') or '').strip()
                    abstract = (cfg.get('subtitle') or '').strip()
                except Exception as e:
                    self.stdout.write(self.style.WARNING("  config.yaml 解析失敗(%s)：%s" % (fname, e)))

            year, week = _week_from_folder(folder)
            if not title:
                title = _md_h1(folder)
            if not title and year and week:
                title = "台股週報｜%d-W%02d" % (year, week)
            if not date and year and week:
                date = _iso_friday(year, week)

            if opts['dry_run']:
                self.stdout.write("  [dry] %s  →  標題「%s」 日期 %s" % (fname, title or '(自動)', date or '(今天)'))
                continue

            try:
                fields, n_img, _ = docx_to_fields(
                    path, title=title, date=date, abstract=abstract,
                    author='史塔克實驗室',
                )
                obj, _action = save_article(1, fields)
                created += 1
                self.stdout.write(self.style.SUCCESS(
                    "  [OK] %s → https://starklab.tw%s（%d 圖）「%s」"
                    % (fname, blog_path(1, obj.id), n_img, fields['title'])
                ))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR("  [FAIL] %s：%s" % (fname, e)))

        self.stdout.write(self.style.SUCCESS(
            "\n完成：新增 %d，跳過 %d，失敗 %d（共 %d）" % (created, skipped, failed, len(docx_paths))
        ))
