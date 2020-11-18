import numpy as np
import sqlite3
import pandas as pd
import csv
from datetime import datetime, timedelta
import time
import datetime
import requests
from io import StringIO


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


txt = input('請輸入你文件的名稱：')

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


nowyear = input('請輸入今天的年份：')
nowmonth = input('請輸入今天的月份：')
nowday = input('請輸入今天的日期：')


predictyear = input('請輸入預測的年份：')
predictmonth = input('請輸入預測的月份')

predict_day=nowyear+predictmonth+"11"
now_day=nowyear+nowmonth+nowday


#取出上市個股數值
for i in range(100):
    try:
        df_last_month=stock_value(predict_day)
        break
    except:
        from datetime import datetime
        edit_time=datetime.strptime(predict_day, "%Y%m%d")
        import datetime
        predict_day= (edit_time+datetime.timedelta(days=-1)).strftime("%Y%m%d")
        
        
for i in range(100):
    try:
        df_now=stock_value(now_day)
        break
    except:
        from datetime import datetime
        edit_time=datetime.strptime(now_day, "%Y%m%d")
        import datetime
        now_day= (edit_time+datetime.timedelta(days=-1)).strftime("%Y%m%d")
        
        






nowyear2=str(int(nowyear)-1911)
predictyear2=str(int(predictyear)-1911)
predict_day2=predictyear2+"/"+predictmonth+"/"+"11"
now_day2=nowyear2+"/"+nowmonth+"/"+nowday




#取出上櫃個股數值
for i in range(100):
    try:
        print(predict_day2)
        df2_last_month=stock_value2(predict_day2)
        break
    except:
        from datetime import datetime
        predict_day_temp=str(int(predict_day2[0:3])+1911)+predict_day2[3:]
        edit_time=datetime.strptime(predict_day_temp, "%Y/%m/%d")
        import datetime
        predict_day_temp= (edit_time+datetime.timedelta(days=-1)).strftime("%Y/%m/%d")
        predict_day_temp_year=str(int(predict_day_temp[0:4])-1911)
        predict_day2=  predict_day_temp_year+predict_day_temp[4:]                                 
        print(predict_day2)                               
                                          
for i in range(100):
    try:
        print(now_day2)
        df2_now=stock_value2(now_day2)
        break
    except:
        from datetime import datetime
        now_day_temp=str(int(now_day2[0:3])+1911)+now_day2[3:]
        
        edit_time=datetime.strptime(now_day_temp, "%Y/%m/%d")
        import datetime
        now_day_temp= (edit_time+datetime.timedelta(days=-1)).strftime("%Y/%m/%d")
        now_day_temp_year=str(int(now_day_temp[0:4])-1911)
        now_day2=  now_day_temp_year+now_day_temp[4:]                                 
       
        print(now_day2)      




df=df_now
for i in range(len(month_predict)):
    a=df[pd.to_numeric(df['證券代號'], errors='coerce') == float(month_predict[i])]
    try:
        b=a.values.tolist()[0]
        print(b[0])
    except:
        pass



#把預測的股票價錢都拿出來
now_list=[]
for i in range(len(month_predict)):
    temp=[]
    index=float(month_predict[i])
    #print(type(index),index)
    try:
        start_value=take_value(df_last_month,index)
        end_value=take_value(df_now,index)
    except:
        start_value=take_value2(df2_last_month,index)
        end_value=take_value2(df2_now,index)
    #print(i,str(index).replace(".0",""),start_value,end_value)
    temp.append(str(index).replace(".0",""))
    temp.append("")
    temp.append(start_value)
    temp.append(end_value)
    now_list.append(temp)





# #不要亂執行   拿來刪檔案用得
# db =  sqlite3.connect('db.sqlite3')
# ##db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
# db.execute("delete from basicHistory")
# db.commit()
# db =  sqlite3.connect('db.sqlite3')
# ##db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
# #db.execute("delete from technicHistory")
# db.commit()



over_date=predictyear+"-"+str(int(predictmonth)+1)+"-"+"11"

# 更新月營收策略  當月股價
# for i in range(len(now_list)):
#     final_update,name,start_date,start_price,current_price,now_return,types=change_parameter(now_list[i]) 
#     print(final_update,name,start_date,start_price,over_date,current_price,now_return,types)


    



# 更新月營收策略  當月股價
db =  sqlite3.connect('db.sqlite3')
#db.execute("INSERT INTO type_data (tag)   VALUES ('{}')".format(data))
db.execute("delete from technicCurrent")
db.commit()
pk=1
for i in range(len(now_list)):
    final_update,name,start_date,start_price,current_price,now_return,types=change_parameter(now_list[i]) 
    over_date=predictyear+"-"+str(int(predictmonth)+1)+"-"+"11"
    print(final_update,name,start_date,start_price,over_date,current_price,now_return,types)
    db =  sqlite3.connect('db.sqlite3')
    db.execute("INSERT INTO technicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type)   VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(pk,final_update,name,start_date,start_price,over_date,current_price,now_return,types))
    db.commit()
    db.close()
    pk=pk+1