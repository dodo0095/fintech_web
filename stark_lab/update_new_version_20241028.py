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



#抓取現在的時間
def take_time():
    from time import gmtime, strftime
    a=strftime("%Y%m%d", gmtime())
    return a[0:4],a[4:6],a[6:8]
    
    

# 抓上市公司股價
def stock_value(datestr):
    #把當月11號的台股資訊 更新
    #datestr = '20200911'
    # 下載股價
    r = requests.post('https://www.twse.com.tw/exchangeReport/MI_INDEX?response=csv&date=' + datestr + '&type=ALL')
    # 整理資料，變成表格
    df = pd.read_csv(StringIO(r.text.replace("=", "")), 
                header=["證券代號" in l for l in r.text.split("\n")].index(True)-1)
    # 整理一些字串：
    df = df.apply(lambda s: pd.to_numeric(s.astype(str).str.replace(",", "").replace("+", "1").replace("-", "-1"), errors='coerce'))
    # 顯示出來
    #df.head()
    return df




#抓上櫃公司股價
def stock_value2(datestr):
    link = 'http://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_download.php?l=zh-tw&d='+datestr+'&s=0,asc,0'
    r = requests.get(link)
    r.ok
    lines = r.text.replace('\r', '').split('\n')
    df = pd.read_csv(StringIO("\n".join(lines[3:])), header=None)
    #df.head()
    df.columns = list(map(lambda l: l.replace(' ',''), lines[2].split(',')))
    #df.index = df['代號']
    #df = df.drop(['代號'], axis=1)
    #df.head()
    return df

#拿上市收盤價資料
def take_value(df,id):
    take_info=df[pd.to_numeric(df['證券代號'], errors='coerce') == id]
    value=float(take_info["收盤價"].values)
    return value
#拿上櫃收盤價資料
def take_value2(df,id):
    take_info=df[pd.to_numeric(df['代號'], errors='coerce') == id]
    value=float(take_info["收盤"].values)
    return value

def change_parameter(save_list):
    final_update=now_day[:4]+"-"+now_day[4:6]+"-"+now_day[6:8]
    name=search_name(now_list[i][0]).replace("\u3000", " ")
    start_date=predict_day[:4]+"-"+predict_day[4:6]+"-"+predict_day[6:8]
    start_price=now_list[i][2]
    
    current_price=now_list[i][3]

    now_return=(float(current_price)-float(start_price))/float(start_price)
    now_return= round(now_return*100,2)

    if float(now_return)>0:
        types="+"
    else:
        types="-"
    return final_update,name,start_date,start_price,current_price,now_return,types

#查詢list in str
#any('1101' in item for item in a)
#查詢list in str
def search_name(name):
    company=[]
    df = pd.read_csv('公司/上市.csv')  
    a=df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/上櫃.csv')  
    b=df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/興櫃.csv')  
    c=df["有價證券代號及名稱"].tolist()
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
    return company

def change(now_day):
    from datetime import datetime, timedelta


    # 將字串轉換為日期物件
    date_obj = datetime.strptime(now_day, "%Y-%m-%d")

    # 加一天
    next_day = date_obj + timedelta(days=1)

    # 將日期物件轉換回字串
    next_day_str = next_day.strftime("%Y-%m-%d")
    return (next_day_str)

with open('data.txt', 'r') as f:
    myNames = [line.strip() for line in f]
    
txt=myNames[0]+"-2"
#txt = input('請輸入你文件的名稱：')

## Open file   把當月份的代號txt  拿出來
doc_name=txt+".txt"
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



nowyear,nowmonth,nowday=take_time()


# nowyear = input('請輸入今天的年份：')
# nowmonth = input('請輸入今天的月份：')
# nowday = input('請輸入今天的日期：')

predictyear=myNames[0][0:4]
predictmonth=myNames[0][4:6]

#predictyear = input('請輸入預測的年份：')
#predictmonth = input('請輸入預測的月份：')


predict_day=predictyear+"-"+predictmonth+"-"+"11"
now_day=nowyear+"-"+nowmonth+"-"+nowday





if int(predictmonth)<12:
	over_date=predictyear+"-"+str(int(predictmonth)+1)+"-"+"11"
elif int(predictmonth)==12:
	#over_date=str(int(predictyear+1))+"-"+"01"+"-"+"11"
	over_date = str(int(predictyear) + 1) + "-" + "01" + "-" + "11"




def get_price_difference(stock_symbol, start_date, end_date):
    # 抓取指定股票的歷史數據
    stock_data = yf.download(stock_symbol, start=start_date, end=end_date)
    
    # 檢查資料是否正確抓取
    if stock_data.empty:
        return "No data found for {stock_symbol} between {start_date} and {end_date}."
    
    # 獲取起始日期與結束日期的收盤價
    start_price = stock_data['Close'].iloc[0]
    end_price = stock_data['Close'].iloc[-1]
    
    # 計算價格差
    price_difference = end_price - start_price

    # 結果輸出
    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_price": round(start_price,2),
        "end_price": round(end_price,2),
        "price_difference": price_difference
    }


# 更新月營收策略  當月股價
db =  sqlite3.connect('db.sqlite3')
#db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
db.execute("delete from technicCurrent")
db.commit()
pk=1
for i in range(len(month_predict)):
    final_update=now_day
    name=search_name(month_predict[i]).replace("\u3000", " ")
    start_date=predict_day
    next_day=change(now_day)
    end_date=next_day
    
    try:
        stock_symbol=month_predict[i]+".TW"
        result = get_price_difference(stock_symbol, start_date, end_date)
        start_price= result["start_price"]
        current_price=result["end_price"]
    except:
        stock_symbol=month_predict[i]+".TWO"
        result = get_price_difference(stock_symbol, start_date, end_date)
        start_price= result["start_price"]
        current_price=result["end_price"]


    start_price= result["start_price"]
    current_price=result["end_price"]
    now_return=(float(current_price)-float(start_price))/float(start_price)
    now_return= round(now_return*100,2)

    if float(now_return)>0:
        types="+"
    else:
        types="-"

    if predictmonth=="12":
        predictmonth="01"  
        over_date=predictyear+"-"+str(int(predictmonth))+"-"+"11" 
    else:
        over_date=predictyear+"-"+str(int(predictmonth)+1)+"-"+"11" 
    print(final_update,name,start_date,start_price,over_date,current_price,now_return,types)
    db =  sqlite3.connect('db.sqlite3')
    db.execute("INSERT INTO technicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type)   VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(pk,final_update,name,start_date,start_price,over_date,current_price,now_return,types))
    db.commit()
    db.close()
    pk=pk+1







# 更新月營收策略  當月股價  basicCurrent
db =  sqlite3.connect('db.sqlite3')
#db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
db.execute("delete from basicCurrent")
db.commit()
pk=1
for i in range(len(month_predict)):
    final_update=now_day
    name=search_name(month_predict[i]).replace("\u3000", " ")
    start_date=predict_day
    end_date=now_day
    
    try:
        stock_symbol=month_predict[i]+".TW"
        result = get_price_difference(stock_symbol, start_date, end_date)
        start_price= result["start_price"]
        current_price=result["end_price"]
    except:
        stock_symbol=month_predict[i]+".TWO"
        result = get_price_difference(stock_symbol, start_date, end_date)
        start_price= result["start_price"]
        current_price=result["end_price"]


    start_price= result["start_price"]
    current_price=result["end_price"]
    now_return=(float(current_price)-float(start_price))/float(start_price)
    now_return= round(now_return*100,2)

    if float(now_return)>0:
        types="+"
    else:
        types="-"

    if predictmonth=="12":
        predictmonth="01"  
        over_date=predictyear+"-"+str(int(predictmonth))+"-"+"11" 
    else:
        over_date=predictyear+"-"+str(int(predictmonth)+1)+"-"+"11" 
    print(final_update,name,start_date,start_price,over_date,current_price,now_return,types)
    db =  sqlite3.connect('db.sqlite3')
    db.execute("INSERT INTO basicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type)   VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(pk,final_update,name,start_date,start_price,over_date,current_price,now_return,types))
    db.commit()
    db.close()
    pk=pk+1



