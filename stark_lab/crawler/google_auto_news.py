import requests 
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import csv
import sqlite3
from datetime import datetime, timedelta
import time


def save(date,source,keyword,title,content,href):
    for i in range(len(content)):
        db =  sqlite3.connect('C:/Users/BANDAI/Desktop/fintech_web/stark_lab/stock.db')
        cursor = db.execute("SELECT * from Google_NEWS WHERE Title==? and  keyword==?",(title[i],keyword,))
        row=cursor.fetchall()
        if len(row)>0:
            print("重複  不存入")
            
        else:
            db.execute("INSERT INTO Google_NEWS (Date,Source,keyword,Title,Content,Link)   VALUES ({},'{}','{}','{}','{}','{}')".format(date,source,keyword,title[i],content[i],href[i]))
            db.commit()
            print("save ok")
    db.close()

def read():
    db = sqlite3.connect('C:/Users/BANDAI/Desktop/fintech_web/stark_lab/stock.db')
    cursor = db.execute("SELECT * from Google_NEWS")
    row=cursor.fetchall()
    db.close()
    return row


def take_company_list(company,path):
    temp=[]
    with open(path, newline='',encoding="utf-8") as csvfile:
        rows = csv.reader(csvfile, delimiter=',')
        for row in rows:
            a=row[0].split()
    #        company.append(a[1])
            temp.append(a)
    del temp[0]
    for i in range(len(temp)):
        company.append(temp[i][1]+" "+temp[i][0])
    return company



company=[]
company=take_company_list(company,"上市.csv")
company=take_company_list(company,"上櫃.csv")
company=take_company_list(company,"興櫃.csv")





# google 抓取新聞存料庫
now=datetime.now().strftime('%Y%m%d')
source="google"

for i in range(len(company)):
    keyword_o = company[i]
    print(keyword_o)
    keyword=urllib.parse.quote(keyword_o)
    topic=[]
    href=[]
    content=[]
    time.sleep(5)
    try:
        url = "https://news.google.com/search?q="+keyword+"&hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant"
        #https://news.google.com/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx6TVdZU0JYcG9MVlJYR2dKVVZ5Z0FQAQ?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant"
        r = requests.get(url)
        web_content = r.text
        soup = BeautifulSoup(web_content,'lxml')
        title = soup.find_all('a', class_='DY5T1d')
        
          
        #print(title)
        for i in range(10):
            #print(title[i].text)
            #a="https://news.google.com"+title[i]["href"].replace(".","")
            #print(a,"\n")
            topic.append(title[i].text)
            href.append("http://news.google.com"+title[i]["href"][1:])
            
            #內文
            temp=""
            url ="http://news.google.com"+title[i]["href"][1:]
            r = requests.get(url)
            web_content = r.text
            soup = BeautifulSoup(web_content,'lxml')
            content_temp = soup.find_all('p')
            for z in range(len(content_temp)):
                content_temp[z]=content_temp[z].text
                temp=temp+content_temp[z]
            content.append(temp)
    except:
        print("fail")
        pass
    save(now,source,keyword_o,topic,content,href)
