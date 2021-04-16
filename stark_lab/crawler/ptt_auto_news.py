
# step1. import package 
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import csv
import sqlite3
from datetime import datetime, timedelta
import time



def check_repeat_data(date,author,title,content,href,score,all_data):
    temp=0

    for i in range(len(title)):
        for j in range(len(all_data)):
            if all_data[j].title==title[i]:
                print(all_data[j].title)  
                print("寫入失敗")
                temp=0
                break
            else:
                temp=1
        if temp==1:
            pttdata.objects.create(date=date[i],author=author[i],title=title[i],content=content[i],href=href[i],pushcount=score[i])
            temp=0


            
            

PTT_URL = 'https://www.ptt.cc'
#API_KEY = '26266720e9aa08a4477f6ed04c1404ec'

def change2content(soup):
    content = soup.find(id="main-content").text
    target_content = u'※ 發信站: 批踢踢實業坊(ptt.cc),'
    #去除掉 target_content
    content = content.split(target_content)
    #print(content)
    #content = content[0].split(date)
    #print(content)
    #去除掉文末 --
    main_content = content[0].replace('--', '')
    #印出內文
    #print(main_content)
    return main_content
    
    
def change2time(soup):
    main_content = soup.find(id="main-content")
    metas = main_content.select('div.article-metaline')
    try:
        if metas==[]:
            date='Tue Aug 20 23:05:13 2019'
            pass
        else:
            date = metas[2].select('span.article-meta-value')[0].string
    except:
    	date=datetime.now().strftime('%a %b %d %H:%M:%S %Y')
    
    return date

def get_web_page(url):
    resp = requests.get(
        url=url,
        cookies={'over18': '1'}
    )
    if resp.status_code != 200:
        print('Invalid url:', resp.url)
        return None
    else:
        return resp.text


def get_articles(dom, date):
    soup = BeautifulSoup(dom, 'html5lib')

    # 取得上一頁的連結
    paging_div = soup.find('div', 'btn-group btn-group-paging')
    prev_url = paging_div.find_all('a')[1]['href']

    articles = []  # 儲存取得的文章資料
    divs = soup.find_all('div', 'r-ent')
    for d in divs:
        if d.find('div', 'date').text.strip() == date:  # 發文日期正確
            # 取得推文數
            push_count = 0
            push_str = d.find('div', 'nrec').text
            if push_str:
                try:
                    push_count = int(push_str)  # 轉換字串為數字
                except ValueError:
                    # 若轉換失敗，可能是'爆'或 'X1', 'X2', ...
                    # 若不是, 不做任何事，push_count 保持為 0
                    if push_str == '爆':
                        push_count = 99
                    elif push_str.startswith('X'):
                        push_count = -10

            # 取得文章連結及標題
            if d.find('a'):  # 有超連結，表示文章存在，未被刪除
                href = d.find('a')['href']
                title = d.find('a').text
                author = d.find('div', 'author').text if d.find('div', 'author') else ''
                articles.append({
                    'title': title,
                    'href': href,
                    'push_count': push_count,
                    'author': author
                })
    return articles, prev_url



def change2content(soup):
    content = soup.find(id="main-content").text
    target_content = u'※ 發信站: 批踢踢實業坊(ptt.cc),'
    #去除掉 target_content
    content = content.split(target_content)
    #print(content)
    #content = content[0].split(date)
    #print(content)
    #去除掉文末 --
    main_content = content[0].replace('--', '')
    main_content = content[0].replace('\n', '')
    #印出內文
    #print(main_content)
    return main_content






def ptt_crawl():

    print('取得今日文章列表...')
    current_page = get_web_page(PTT_URL + '/bbs/Stock/index.html')
    if current_page:
        articles = []  # 全部的今日文章
        author=[]
        content=[]
        title=[]
        href=[]
        date=[]
        score=[]
        today = time.strftime('%m/%d').lstrip('0') 

        current_articles, prev_url = get_articles(current_page, today)  # 目前頁面的今日文章
        while current_articles:  # 若目前頁面有今日文章則加入 articles，並回到上一頁繼續尋找是否有今日文章
            articles += current_articles
            current_page = get_web_page(PTT_URL + prev_url)
            current_articles, prev_url = get_articles(current_page, today)
        print('共 %d 篇文章' % (len(articles)))
        # 已取得文章列表，開始進入各文章尋找發文者 IP
  
        for article in articles[:9999]:
            page=requests.get(PTT_URL + article['href'])
            soup = BeautifulSoup(page.text, 'html.parser')
            temp=change2time(soup)
            temp=datetime.strptime(temp, "%a %b %d %H:%M:%S %Y")
            temp=temp.strftime("%Y-%m-%d %H:%M")
            date.append(temp)    #時間
            author.append(article['author'])  #作者
            title_temp=article['title'].replace("'","")
     
            title.append(title_temp)    #標題
            temp=change2content(soup)
            temp=temp.replace("'","")
         
            content.append(temp)  #內文
            href.append(PTT_URL+article['href'])      #連結
            score.append(article['push_count']) #需推文
            total_article=len(score)
    return date,author,content,title,score,href

def save(date,author,content,title,score,href):
    now=datetime.now().strftime('%Y-%m-%d')
    db = sqlite3.connect('C:/Users/BANDAI/Desktop/fintech_web/stark_lab/stock.db')
    cursor = db.execute("SELECT title from PTT_NEWS WHERE date LIKE ? ",('%'+now+'%',))
    row=cursor.fetchall()
    temp=0
    if len(row)==0:
        for i in range(len(title)):  
            db.execute("INSERT INTO PTT_NEWS (date,author,title,href,pushcount,content)   VALUES ('{}','{}','{}','{}','{}','{}')".format(date[i],author[i],title[i],href[i],score[i],content[i]))
            db.commit()
    else:
        for i in range(len(title)):     
            for j in range(len(row)):
                if  title[i]==str(row[j])[2:-3]:
                    print("以重複，存入失敗")
                    temp=0
                    break
                else:
                    temp=1
            if temp==1:
                db.execute("INSERT INTO PTT_NEWS (date,author,title,href,pushcount,content)   VALUES ('{}','{}','{}','{}','{}','{}')".format(date[i],author[i],title[i],href[i],score[i],content[i]))
                db.commit()
                temp=0
    db.close()



def read():
    db = sqlite3.connect('C:/Users/BANDAI/Desktop/-mimir_ver2.0/stock.db')
    cursor = db.execute("SELECT * from PTT_NEWS")
    row=cursor.fetchall()
    db.close()
    return row





date,author,content,title,score,href=ptt_crawl()




save(date,author,content,title,score,href)


