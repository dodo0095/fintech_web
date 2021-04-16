import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
import csv

def save(date,source,keyword,title,content,href):
    
    for i in range(len(date)):
    
        db =  sqlite3.connect('C:/Users/BANDAI/Desktop/fintech_web/stark_lab/stock.db')
        cursor = db.execute("SELECT * from Yahoo_NEWS WHERE Title==? and  keyword==?",(title[i],keyword,))
        row=cursor.fetchall()
        db.close()
        if len(row)>0:
            print("重複  不存入")
        else:
            db.execute("INSERT INTO Yahoo_NEWS (Date,Source,keyword,Title,Content,Link)   VALUES ('{}','{}','{}','{}','{}','{}')".format(date[i],source,keyword,title[i],content[i],href[i]))
            db.commit() 
            print("save ok")
            db.close()

def read():
    db = sqlite3.connect('C:/Users/BANDAI/Desktop/fintech_web/stark_lab/stock.db')
    cursor = db.execute("SELECT * from Yahoo_NEWS")
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
        company.append(temp[i][0])
    return company





company=[]
company=take_company_list(company,"上市.csv")
company=take_company_list(company,"上櫃.csv")
company=take_company_list(company,"興櫃.csv")





# yahoo 抓取新聞存料庫
#now=datetime.now().strftime('%Y%m%d')
source="yahoo"

for i in range(len(company)):
    keyword = company[i]
    print(keyword)
    try:
        topic=[]
        href=[]
        content=[]
        date=[]
        time.sleep(5)
        html = requests.get('https://tw.stock.yahoo.com/q/h?s='+keyword)
        # print(html.text)
        soup = BeautifulSoup(html.text, 'html.parser')
        getAllNew=(soup.find('table'))
        getNews = getAllNew.find_all('table',{'width':'100%'})
        news_nuumber=len(getNews[0].findAll('a'))
        for i in range(news_nuumber):
            temp=""
            html=requests.get("https://tw.stock.yahoo.com/"+getNews[0].findAll('a')[i]["href"])
            soup=BeautifulSoup(html.text, 'html.parser')
            word=soup.find_all("p")
            for j in range(2,len(word)-2,1):  
                temp=temp+word[j].text
            time_s=soup.find_all(class_="caas-attr-meta-time")
            time_s=time_s[0].text
            #print(getNews[0].findAll('a')[i].text)
            #print("https://tw.stock.yahoo.com/"+getNews[0].findAll('a')[i]["href"])
            #print(temp)
            #print("")
            topic_temp=getNews[0].findAll('a')[i].text.replace("'","")
            topic_temp=topic_temp.replace('"','')
            topic.append(topic_temp)
            href.append("https://tw.stock.yahoo.com/"+getNews[0].findAll('a')[i]["href"])
            content.append(temp)
            date.append(time_s)        
    except:
        pass
    try:
        save(date,source,keyword,topic,content,href)
    except:
        pass
