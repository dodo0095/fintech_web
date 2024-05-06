import numpy as np
import sqlite3
import pandas as pd
import csv
from datetime import datetime, timedelta
import time
import datetime
import requests
from io import StringIO
import yfinance as yf
from datetime import datetime, timedelta

#抓取現在的時間
def take_time():
    from time import gmtime, strftime
    a=strftime("%Y%m%d", gmtime())
    return a[0:4],a[4:6],a[6:8]

## Open file   把當月份的代號txt  拿出來
def take_month_predict():
    nowyear,nowmonth,nowday=take_time()
    if int(nowday) > 11:
        pass
    else:
        if int(nowmonth)==1:
            nowmonth=12
            nowyear=int(nowyear)-1
        else:
            nowmonth=int(nowmonth)-1
    nowmonth=str(nowmonth)
    if len((nowmonth))==1:
        nowmonth="0"+nowmonth
    nowyear=str(nowyear)
    
    doc_name=nowyear+nowmonth+".txt"
    fp = open(doc_name, "r")
    line = fp.readline()
    month_predict=[]
    ## 用 while 逐行讀取檔案內容，直至檔案結尾
    while line:
    #    print (line)
        line=line.replace(" ","")
        month_predict.append(line.replace("\n",""))
        line = fp.readline()
    fp.close()
    return month_predict
    
## Open file   指定 月份的代號txt  拿出來
def take_month_predict2(filename):
    filename=str(filename)
    doc_name= filename +".txt"   #修改這邊就好了
    
    fp = open(doc_name, "r")
    line = fp.readline()
    month_predict=[]
    ## 用 while 逐行讀取檔案內容，直至檔案結尾
    while line:
    #    print (line)
        line=line.replace(" ","")
        month_predict.append(line.replace("\n",""))
        line = fp.readline()
    fp.close()
    return month_predict




## 更新最新的txt
month_predict=take_month_predict()
## Open file   指定 月份的代號txt  拿出來
# take_month_predict2(202402)



#取得初始報價 ， 當天報價也可以用這個function

def get_start_price(year,month,day,stock_symbol):

    # 獲取台積電股票
    #stock_symbol = "2330.tw"  # 台積電在 Yahoo Finance 的代號
    stock = yf.Ticker(stock_symbol)

    # 設定目標日期
    # 指定某個月的11號
    target_date = datetime(year=year, month=month, day=day)

    # 獲取指定日期的股票歷史資料
    # 使用 period="1d" 表示只要那一天的資料
    stock_history = stock.history(start=target_date.strftime("%Y-%m-%d"), end=(target_date + timedelta(days=1)).strftime("%Y-%m-%d"))

    # 確保獲得資料
    if not stock_history.empty:
        # 打印收盤價
        closing_price = stock_history['Close'][0]
        #print(stock_symbol,f"這支股票在 {target_date.strftime('%Y年%m月%d日')} 的收盤價為: {closing_price}")
        return round(closing_price,2),target_date.strftime("%Y-%m-%d")
    else:

        print("未找到指定日期的資料 往前一天")
        target_date = target_date + timedelta(days=-1)
        year_1 = target_date.year
        month_1 = target_date.month
        day_1 = target_date.day
        get_start_price(year_1,month_1,day_1,stock_symbol)
    
        
#取得最後報價

def get_final_price(year,month,day,stock_symbol):

    # 獲取台積電股票
    #stock_symbol = "2330.tw"  # 台積電在 Yahoo Finance 的代號
    stock = yf.Ticker(stock_symbol)

    # 設定目標日期
    # 指定某個月的11號
    target_date = datetime(year=year, month=month, day=day)

    # 獲取指定日期的股票歷史資料
    # 使用 period="1d" 表示只要那一天的資料
    stock_history = stock.history(start=target_date.strftime("%Y-%m-%d"), end=(target_date + timedelta(days=1)).strftime("%Y-%m-%d"))

    # 確保獲得資料
    if not stock_history.empty:
        # 打印收盤價
        closing_price = stock_history['Close'][0]
        #print(stock_symbol,f"這支股票在 {target_date.strftime('%Y年%m月%d日')} 的收盤價為: {closing_price}")
        return round(closing_price,2),target_date.strftime("%Y-%m-%d")
    else:

        print("未找到指定日期的資料 往後一天")
        target_date = target_date + timedelta(days=1)
        year_1 = target_date.year
        month_1 = target_date.month
        day_1 = target_date.day
        get_final_price(year_1,month_1,day_1,stock_symbol)
    
        


#取得預測結束日期
def get_over_date():
    nowyear,nowmonth,nowday=take_time()
    if int(nowday) > 11:
        pass
    else:
        if int(nowmonth)==1:
            nowmonth=12
            nowyear=int(nowyear)-1
        else:
            nowmonth=int(nowmonth)-1
    predictmonth=str(nowmonth)
    predictyear=str(nowyear)
    
    over_date=predictyear+"-"+str(int(predictmonth)+1)+"-"+"11"
    
    return over_date


#對應公司名稱
def search_name(name):
    company=[]
    df = pd.read_csv('公司/上市.csv')  
    a=df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/上櫃.csv')  
    b=df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/興櫃.csv')  
    c=df["有價證券代號及名稱"].tolist()
    try:
        for i in a:
            if i.__contains__(name) :
                company=i
                #print(i, " is containing")
        for i in b:
            if i.__contains__(name) :
                company=i
                #print(i, " is containing")
        for i in c:
            if i.__contains__(name) :
                company=i
                #print(i, " is containing")
        return company.replace("\u3000", " ")
    except:
        return name
def check_tw_two(name):
    company=[]
    df = pd.read_csv('公司/上市.csv')  
    a=df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/上櫃.csv')  
    b=df["有價證券代號及名稱"].tolist()

    try:
        for i in a:
            if i.__contains__(name) :
                company=i
                #print(i, " is containing")
                return name+".tw"
        for i in b:
            if i.__contains__(name) :
                company=i
                #print(i, " is containing")
                return name+".two"
    except:
        return name
def get_information(stock_symbol):

    #得到所有資訊

    #得到公司名字
    name=search_name(stock_symbol)
    
    
    #先得到初始價格跟時間
    year,month,day=take_time()
    if int(day)<11:
        month=int(month)-1
    start_price,start_date=get_start_price(int(year),int(month),11,check_tw_two(stock_symbol))

    #再得到目前的價格跟時間
    year,month,day=take_time()
    current_price,final_update=get_final_price(int(year),int(month),int(day),check_tw_two(stock_symbol))

    #得到報酬率
    now_return=(float(current_price)-float(start_price))/float(start_price)
    now_return= round(now_return*100,2)
    #print(now_return)
    if float(now_return)>0:
        types="+"
    else:
        types="-"
    print(name,start_price,start_date,current_price,final_update,now_return,types)
    return name,start_price,start_date,current_price,final_update,now_return,types


print("更新 basicCurrent db")


#更新左邊的
# 更新月營收策略  當月股價
db =  sqlite3.connect('db.sqlite3')
#db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
db.execute("delete from basicCurrent")
db.commit()
pk=1

#得到最後日期
over_date=get_over_date()
#寫進資料庫
for i in range(len(month_predict)):
    name,start_price,start_date,current_price,final_update,now_return,types=get_information(month_predict[i])

    #print(final_update,name,start_date,start_price,over_date,current_price,now_return,types)
    
    db =  sqlite3.connect('db.sqlite3')
    db.execute("INSERT INTO basicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type)   VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(pk,final_update,name,start_date,start_price,over_date,current_price,now_return,types))
    db.commit()
    db.close()
    pk=pk+1





print("更新technicCurrent db")

#更新右邊的
# 更新月營收策略  當月股價
db =  sqlite3.connect('db.sqlite3')
#db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
db.execute("delete from technicCurrent")
db.commit()
pk=1

#得到最後日期
over_date=get_over_date()
#寫進資料庫
for i in range(len(month_predict)):
    name,start_price,start_date,current_price,final_update,now_return,types=get_information(month_predict[i])

    #print(final_update,name,start_date,start_price,over_date,current_price,now_return,types)
    
    db =  sqlite3.connect('db.sqlite3')
    db.execute("INSERT INTO technicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type)   VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(pk,final_update,name,start_date,start_price,over_date,current_price,now_return,types))
    db.commit()
    db.close()
    pk=pk+1
