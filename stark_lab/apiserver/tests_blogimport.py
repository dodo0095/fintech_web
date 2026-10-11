import base64
import os
import shutil
import tempfile
import zipfile
from io import StringIO
from xml.sax.saxutils import escape

from bs4 import BeautifulSoup
from django.core.management import call_command
from django.test import TestCase, override_settings

from apiserver.blogimport import (
    ABSTRACT_MAX_CHARS,
    ELLIPSIS,
    HEADING_TAGS,
    demote_headings,
    docx_to_fields,
    extract_abstract,
    fill_missing_alts,
    truncate_text,
)
from apiserver.models import article_1

# 1x1 透明 PNG
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

W_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '</Types>'
)

PACKAGE_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    '</Relationships>'
)

STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles %s>'
    '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>'
    '</w:styles>' % W_NS
)


def _paragraph(text, style=''):
    ppr = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else ''
    return '<w:p>%s<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (ppr, escape(text))


def _image_paragraph(index, rel_id, descr):
    descr_attr = ' descr="%s"' % escape(descr) if descr else ''
    return (
        '<w:p><w:r><w:drawing><wp:inline>'
        '<wp:extent cx="9525" cy="9525"/>'
        '<wp:docPr id="%d" name="Picture %d"%s/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="%d" name="img%d.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/></pic:blipFill></pic:pic>'
        '</a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r></w:p>'
    ) % (index, index, descr_attr, index, index, rel_id)


def build_docx(path, blocks):
    """產生最小可用的 .docx。

    blocks 元素：('h1', 文字) / ('h2', 文字) / ('p', 文字) / ('img', 圖片描述或 '')。
    """
    body, rels, images = [], [], 0
    for kind, value in blocks:
        if kind == 'img':
            images += 1
            rel_id = 'rIdImg%d' % images
            rels.append(
                '<Relationship Id="%s" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                'Target="media/image%d.png"/>' % (rel_id, images)
            )
            body.append(_image_paragraph(images, rel_id, value))
        elif kind in ('h1', 'h2'):
            body.append(_paragraph(value, 'Heading%s' % kind[1]))
        else:
            body.append(_paragraph(value))

    rels.append(
        '<Relationship Id="rIdStyles" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document %s><w:body>%s</w:body></w:document>' % (W_NS, ''.join(body))
    )
    document_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '%s</Relationships>' % ''.join(rels)
    )
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', CONTENT_TYPES)
        zf.writestr('_rels/.rels', PACKAGE_RELS)
        zf.writestr('word/document.xml', document)
        zf.writestr('word/_rels/document.xml.rels', document_rels)
        zf.writestr('word/styles.xml', STYLES)
        for n in range(1, images + 1):
            zf.writestr('word/media/image%d.png' % n, PNG_BYTES)


LEAD = "這一週台股又讓人坐了一次雲霄飛車，加權指數單日重挫六百點，外資趁機調節籌碼，電子類股指數跌幅超過三個百分點，市場情緒急速降溫。"
LONG_LEAD = LEAD * 3


def weekly_blocks(lead=LEAD, body_text="正文內容"):
    return [
        ('p', '千點驚魂之後的訊號'),
        ('p', '台股週報 2026 W14｜2026.03.30 – 04.04'),
        ('p', '平台：方格子（Vocus）｜發布日期：2026-04-05｜作者：史塔克實驗室'),
        ('p', lead),
        ('img', ''),
        ('h1', '一、本週市場'),
        ('h2', '1.1 個股觀察'),
        ('img', 'Word 內的圖片描述'),
        ('p', body_text),
        ('img', ''),
    ]


class TempMediaMixin:
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix='blogimport-test-')
        self.media_override = override_settings(MEDIA_ROOT=os.path.join(self.tmp, 'media'))
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()


class HtmlHelperTests(TestCase):
    def test_demote_headings_shifts_every_level_and_caps_at_h6(self):
        soup = BeautifulSoup(
            '<h1>a</h1><h2>b</h2><h3>c</h3><h4>d</h4><h5>e</h5><h6>f</h6>', 'html.parser'
        )

        demote_headings(soup)

        self.assertEqual(
            [t.name for t in soup.find_all(True)], ['h2', 'h3', 'h4', 'h5', 'h6', 'h6']
        )
        self.assertEqual([t.get_text() for t in soup.find_all(True)], list('abcdef'))

    def test_fill_missing_alts_keeps_existing_and_numbers_by_position(self):
        soup = BeautifulSoup(
            '<img src="1.png"><img src="2.png" alt="既有說明"><img src="3.png" alt="  ">',
            'html.parser',
        )

        fill_missing_alts(soup, '週報標題')

        self.assertEqual(
            [img['alt'] for img in soup.find_all('img')],
            ['週報標題 圖1', '既有說明', '週報標題 圖3'],
        )

    def test_truncate_text(self):
        self.assertEqual(truncate_text('短文'), '短文')
        exact = 'x' * ABSTRACT_MAX_CHARS
        self.assertEqual(truncate_text(exact), exact)
        self.assertEqual(truncate_text(exact + 'y'), exact + ELLIPSIS)

    def test_extract_abstract_skips_short_paragraphs(self):
        soup = BeautifulSoup(
            '<p>副標</p><p></p><p>台股週報 2026 W14｜2026.03.30 – 04.04</p><p>%s</p>' % LEAD,
            'html.parser',
        )

        self.assertEqual(extract_abstract(soup), LEAD)

    def test_extract_abstract_truncates_long_paragraph(self):
        soup = BeautifulSoup('<p>%s</p>' % LONG_LEAD, 'html.parser')

        abstract = extract_abstract(soup)

        self.assertEqual(len(abstract), ABSTRACT_MAX_CHARS + len(ELLIPSIS))
        self.assertTrue(abstract.endswith(ELLIPSIS))
        self.assertTrue(LONG_LEAD.startswith(abstract[:-1]))

    def test_extract_abstract_falls_back_to_first_text_when_all_short(self):
        soup = BeautifulSoup('<p></p><p>只有短句</p><p>另一短句</p>', 'html.parser')

        self.assertEqual(extract_abstract(soup), '只有短句')


class DocxToFieldsTests(TempMediaMixin, TestCase):
    def convert(self, blocks, **kwargs):
        path = os.path.join(self.tmp, 'sample.docx')
        build_docx(path, blocks)
        fields, image_count, _ = docx_to_fields(path, **kwargs)
        return fields, image_count, BeautifulSoup(fields['content'], 'html.parser')

    def test_content_has_no_h1_and_headings_are_demoted(self):
        fields, _, soup = self.convert(weekly_blocks(), title='週報標題')

        self.assertEqual(soup.find_all('h1'), [])
        self.assertEqual([h.name for h in soup.find_all(['h2', 'h3'])], ['h2', 'h3'])
        self.assertEqual(soup.find('h2').get_text(), '一、本週市場')

    def test_every_image_has_alt_and_word_description_wins(self):
        _, image_count, soup = self.convert(weekly_blocks(), title='週報標題')

        self.assertEqual(image_count, 3)
        self.assertEqual(
            [img.get('alt') for img in soup.find_all('img')],
            ['週報標題 圖1', 'Word 內的圖片描述', '週報標題 圖3'],
        )

    def test_auto_abstract_uses_first_meaningful_paragraph(self):
        fields, _, _ = self.convert(weekly_blocks(), title='週報標題')

        self.assertEqual(fields['abstract'], LEAD)

    def test_auto_abstract_is_truncated_with_ellipsis(self):
        fields, _, _ = self.convert(weekly_blocks(lead=LONG_LEAD), title='週報標題')

        self.assertEqual(len(fields['abstract']), ABSTRACT_MAX_CHARS + len(ELLIPSIS))
        self.assertTrue(fields['abstract'].endswith(ELLIPSIS))

    def test_explicit_abstract_is_kept(self):
        fields, _, _ = self.convert(weekly_blocks(), title='週報標題', abstract='手動摘要')

        self.assertEqual(fields['abstract'], '手動摘要')

    def test_title_taken_from_first_heading_is_removed_before_demotion(self):
        fields, _, soup = self.convert([('h1', '文內標題'), ('p', LEAD), ('h2', '小節')])

        self.assertEqual(fields['title'], '文內標題')
        self.assertNotIn('文內標題', fields['content'])
        self.assertEqual([h.name for h in soup.find_all(HEADING_TAGS)], ['h3'])



class BackfillWeeklyRebuildTests(TempMediaMixin, TestCase):
    WEEKS = ('2026-W14', '2026-W15')

    def setUp(self):
        super().setUp()
        self.articles_dir = os.path.join(self.tmp, 'articles')
        for week in self.WEEKS:
            self.write_week(week, body_text='舊版正文')

    def write_week(self, week, body_text):
        folder = os.path.join(self.articles_dir, week)
        os.makedirs(folder, exist_ok=True)
        build_docx(
            os.path.join(folder, '%s_台股週報_方格子專欄.docx' % week),
            weekly_blocks(body_text=body_text),
        )

    def run_backfill(self, *flags):
        out = StringIO()
        call_command('backfill_weekly', '--dir', self.articles_dir, *flags, stdout=out)
        return out.getvalue()

    def test_rebuild_updates_existing_in_place_without_duplicates(self):
        self.run_backfill()
        ids_before = sorted(article_1.objects.values_list('id', flat=True))
        self.assertEqual(len(ids_before), 2)
        for week in self.WEEKS:
            self.write_week(week, body_text='新版正文')

        output = self.run_backfill('--rebuild')

        self.assertEqual(sorted(article_1.objects.values_list('id', flat=True)), ids_before)
        self.assertIn('更新 2', output)
        for article in article_1.objects.all():
            self.assertIn('新版正文', article.content)
            self.assertNotIn('舊版正文', article.content)
            self.assertNotIn('<h1', article.content)

    def test_rebuild_ignores_mtime_when_source_unchanged(self):
        self.run_backfill()

        output = self.run_backfill('--rebuild')

        self.assertIn('更新 2', output)
        self.assertEqual(article_1.objects.count(), 2)

    def test_rebuild_creates_missing_articles(self):
        self.run_backfill()
        self.write_week('2026-W16', body_text='新週正文')

        output = self.run_backfill('--rebuild')

        self.assertIn('新增 1，更新 2', output)
        self.assertEqual(article_1.objects.count(), 3)

    def test_rebuild_dry_run_writes_nothing(self):
        self.run_backfill()
        before = list(article_1.objects.order_by('id').values_list('id', 'content'))
        for week in self.WEEKS:
            self.write_week(week, body_text='新版正文')

        output = self.run_backfill('--rebuild', '--dry-run')

        self.assertIn('[dry] 更新', output)
        self.assertEqual(list(article_1.objects.order_by('id').values_list('id', 'content')), before)

    def test_force_still_creates_duplicates(self):
        self.run_backfill()

        self.run_backfill('--force')

        self.assertEqual(article_1.objects.count(), 4)
