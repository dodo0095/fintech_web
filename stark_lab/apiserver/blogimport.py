# -*- coding: utf-8 -*-
"""部落格上稿共用核心：Word(.docx) → 文章欄位 → 寫入 article_1/2。

給 management command 使用：
  - publish_docx        單篇上稿
  - backfill_weekly     批次回填週報

不直接依賴 Django 指令環境，方便重用與測試。
"""
import os
import datetime

from django.conf import settings

from apiserver.models import article_1, article_2


def docx_to_fields(docx_path, title='', author='史塔克實驗室', author_pic='',
                   cover='', abstract='', date='', link=''):
    """把 .docx 轉成文章欄位 dict。

    圖片存到 MEDIA_ROOT/blog/<時間戳>/imgN.ext，正文 img src 改寫成 /media/...。
    未指定的欄位會自動推導（標題→第一個 h1/h2→檔名；摘要→第一段；封面→第一張圖；日期→今天）。

    回傳 (fields: dict, image_count: int)。
    """
    import mammoth
    from bs4 import BeautifulSoup

    docx_path = os.path.abspath(docx_path)

    stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    img_dir = os.path.join(settings.MEDIA_ROOT, 'blog', stamp)
    os.makedirs(img_dir, exist_ok=True)
    counter = {'n': 0}

    def convert_image(image):
        counter['n'] += 1
        ext = (image.content_type or 'image/png').split('/')[-1].split('+')[0].lower()
        if ext == 'jpeg':
            ext = 'jpg'
        fname = "img%d.%s" % (counter['n'], ext)
        with image.open() as f:
            data = f.read()
        with open(os.path.join(img_dir, fname), 'wb') as out:
            out.write(data)
        media_url = settings.MEDIA_URL if settings.MEDIA_URL.endswith('/') else settings.MEDIA_URL + '/'
        return {"src": "%sblog/%s/%s" % (media_url, stamp, fname)}

    result = mammoth.convert_to_html(
        docx_path,
        convert_image=mammoth.images.img_element(convert_image),
    )
    messages = [str(m) for m in result.messages]
    soup = BeautifulSoup(result.value, 'html.parser')

    # 標題：傳入 > 第一個 h1/h2 > 檔名
    title = (title or '').strip()
    first_heading = soup.find(['h1', 'h2'])
    if not title and first_heading:
        title = first_heading.get_text(strip=True)
    if not title:
        title = os.path.splitext(os.path.basename(docx_path))[0]
    # 只有在標題確實來自文內第一個標題時，才移除以免重複
    if first_heading and first_heading.get_text(strip=True) == title:
        first_heading.decompose()

    # 封面：傳入 > 文內第一張圖
    cover = (cover or '').strip()
    if not cover:
        first_img = soup.find('img')
        if first_img and first_img.get('src'):
            cover = first_img['src']

    # 摘要：傳入 > 第一段有字的文字（截 100 字）
    abstract = (abstract or '').strip()
    if not abstract:
        for p in soup.find_all('p'):
            txt = p.get_text(strip=True)
            if txt:
                abstract = txt[:100]
                break

    content_html = str(soup).strip()
    date = (date or '').strip() or datetime.date.today().strftime('%Y-%m-%d')
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    fields = dict(
        title=title,
        title_picture=cover,
        abstract=abstract,
        author_picture=(author_pic or '').strip(),
        author_name=(author or '').strip(),
        date=date,
        link=(link or '').strip(),
        content=content_html,
        slug='',
        source_docx=os.path.basename(docx_path),
        updated=now_str,
    )
    return fields, counter['n'], messages


def model_for_cat(cat):
    return article_1 if int(cat) == 1 else article_2


def save_article(cat, fields, update_id=0):
    """建立或更新文章，回傳 (obj, action_str)。"""
    Model = model_for_cat(cat)
    if update_id:
        obj = Model.objects.get(pk=update_id)
        for k, v in fields.items():
            setattr(obj, k, v)
        obj.save()
        return obj, "更新"
    obj = Model.objects.create(**fields)
    return obj, "新增"


def blog_path(cat, pk):
    return "/blog/%d/" % pk if int(cat) == 1 else "/blog/tech/%d/" % pk
