from django.shortcuts import render
# Create your views here.
from rest_framework import viewsets
from apiserver.serializers import  bot_apiSerializer,technicHistory_Serializer,technicCurrent_Serializer
from apiserver.serializers import basicHistory_Serializer,basicCurrent_Serializer,article_Serializer,article2_Serializer
from apiserver.models import bot,technicHistory,technicCurrent,basicHistory,basicCurrent,article_1,article_2
from rest_framework import generics
import django_filters.rest_framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime
import math
import sqlite3
import re
from django.db.models import Q


def sent_dict():
    #輸入情感字典
    with open('NTUSD/negatives整理.txt', mode='r', encoding='utf-8') as f:
        negs = f.readlines()
    with open('NTUSD/positives整理.txt', mode='r', encoding='utf-8') as f:
        poss = f.readlines()
    pos = []
    for i in poss:
        a=re.findall(r'\w+',i) 
        pos.extend(a)
    neg = []
    for i in negs:
        a=re.findall(r'\w+',i) 
        neg.extend(a)
    return pos,neg

def fin_dict():
    #輸入情感字典
    with open('NTUSD/negatives金融.txt', mode='r', encoding='utf-8') as f:
        negs = f.readlines()
    with open('NTUSD/positives金融.txt', mode='r', encoding='utf-8') as f:
        poss = f.readlines()
    pos_fin = []
    for i in poss:
        a=re.findall(r'\w+',i) 
        pos_fin.extend(a)
    neg_fin = []
    for i in negs:
        a=re.findall(r'\w+',i) 
        neg_fin.extend(a)
    return pos_fin,neg_fin





class chose_robot(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    lookup_url_kwarg = "email"
   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = bot_apiSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = bot.objects.all()
        username = self.request.query_params.get('email', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(email=str(username))
        return queryset





class technicHistoryapi(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    lookup_url_kwarg = "email"
   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = technicHistory_Serializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        data = technicHistory.objects.all()
        username = self.request.query_params.get('email', None)
        tableData=[]
        #username=urllib.parse.quote(username)


        temp=0
        today = datetime.date.today()
#        print(today.month,type(today.month)) 
        for i in range(len(data)):
            #print((data[i].start_date)[0:4],(data[i].start_date)[5:7])
            if (data[i].start_date)[0:4]==str((today.year)-1) and (data[i].start_date)[5:7]==str((today.month)) :
                temp=i
                break


        print(temp,i)

        for i in range(temp,len(data),1):
            dict = {'id':data[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':data[i].stock_name,'start_date':data[i].start_date\
                        ,'buy_price':data[i].buy_price\
                        ,'over_date':data[i].over_date\
                        ,'sell_price':data[i].sell_price\
                        ,'return_value':str(round(float(data[i].return_value),2))\
                        ,'type':data[i].type\
                            }
            tableData.append(dict)

        return (tableData)


class technicCurrentapi(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = technicCurrent_Serializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = technicCurrent.objects.all()
        username = self.request.query_params.get('email', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(email=str(username))
        return queryset








class basicHistoryapi(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    lookup_url_kwarg = "email"
   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = basicHistory_Serializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        data = basicHistory.objects.all()
        username = self.request.query_params.get('email', None)
        tableData=[]
        #username=urllib.parse.quote(username)


        temp=0
        today = datetime.date.today()
#        print(today.month,type(today.month)) 
        for i in range(len(data)):
            #print((data[i].start_date)[0:4],(data[i].start_date)[5:7])
            if (data[i].start_date)[0:4]==str((today.year)-1) and (data[i].start_date)[5:7]==str((today.month)) :
                temp=i
                break


        print(temp,i)

        for i in range(temp,len(data),1):
            dict = {'id':data[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':data[i].stock_name,'start_date':data[i].start_date\
                        ,'buy_price':data[i].buy_price\
                        ,'over_date':data[i].over_date\
                        ,'sell_price':data[i].sell_price\
                        ,'return_value':str(round(float(data[i].return_value),2))\
                        ,'type':data[i].type\
                            }
            tableData.append(dict)

        return (tableData)



class basicCurrentapi(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    lookup_url_kwarg = "email"
   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = basicCurrent_Serializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = basicCurrent.objects.all()
        username = self.request.query_params.get('email', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(email=str(username))
        return queryset



from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
def basicCurrentapi2(request):


    dict_finalt={'board':"", 'final_update':"",'tableData':""}
    if request.method == 'GET':
        data = basicCurrent.objects.all()
        tableData=[]
        total_return=0
        total_start_price=0
        total_final_price=0
        for i in range(len(data)):
            dict = {'id':data[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':data[i].stock_name,'start_date':data[i].start_date\
                        ,'start_price':data[i].start_price\
                        ,'over_date':data[i].over_date\
                        ,'current_price':data[i].current_price\
                        ,'now_return':str(round(float(data[i].now_return),2))\
                        ,'type':data[i].type\
                            }
            tableData.append(dict)
            total_return=total_return+float(data[i].now_return)
            total_return=round(total_return,2)
            total_start_price=total_start_price+float(data[i].start_price)
            total_final_price=total_final_price+float(data[i].current_price)

        a=round(((total_final_price-total_start_price)/total_start_price)*100,2)

        board= {"today": 'X',"total":str(a)}
        dict_finalt={'board':board, 'final_update':data[0].final_update,'tableData':tableData}
        return Response(dict_finalt)



@api_view(['GET'])
def technicCurrentapi2(request):


    dict_finalt={'board':"", 'final_update':"",'tableData':""}
    if request.method == 'GET':
        data = technicCurrent.objects.all()
        tableData=[]
        total_return=0
        total_start_price=0
        total_final_price=0
        for i in range(len(data)):
            dict = {'id':data[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':data[i].stock_name,'start_date':data[i].start_date\
                        ,'start_price':data[i].start_price\
                        ,'over_date':data[i].over_date\
                        ,'current_price':data[i].current_price\
                        ,'now_return':str(round(float(data[i].now_return),2))\
                        ,'type':data[i].type\
                            }
            tableData.append(dict)
            total_return=total_return+float(data[i].now_return)
            total_return=round(total_return,2)
            total_start_price=total_start_price+float(data[i].start_price)
            total_final_price=total_final_price+float(data[i].current_price)

        a=round(((total_final_price-total_start_price)/total_start_price)*100,2)

        board= {"today": 'X',"total":str(a)}
        dict_finalt={'board':board, 'final_update':data[0].final_update,'tableData':tableData}
        return Response(dict_finalt)







class articleapi(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    lookup_url_kwarg = "email"
   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = article_Serializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = article_1.objects.all().order_by('-id')
        username = self.request.query_params.get('title', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(title=str(title))
        return queryset



class articleapi2(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    lookup_url_kwarg = "email"
   # queryset = pttdata.objects.filter(id = 412)
    serializer_class = article2_Serializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = article_2.objects.all().order_by('-id')
        username = self.request.query_params.get('title', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(title=str(title))
        return queryset

@api_view(['GET'])
def news_get(request,search):
    search = request.query_params.get('search', None)
    #情緒字典
    
    #pos,neg=fin_dict()
    pos,neg=sent_dict()

    #日期範圍
    time_range=datetime.datetime.now()+datetime.timedelta(days=-5)
    time_range=time_range.strftime("%Y-%m-%d")


    content_all=[]
    content_all_date=[]

    #拿ptt資料
    db =  sqlite3.connect('stock.db')
    cursor = db.execute("SELECT * from PTT_NEWS where title like ? ", ('%{}%'.format(search),))
    data=cursor.fetchall()
    db.close()
    #print(data[0][0])
    ptt=[]

    for i in range(len(data)-1,1,-1):
        if data[i][0][0:10]>time_range:
            temp = {'value':data[i][2]\
                        #,'final_update':data[i].final_update\
                        ,'link':data[i][3]\
                        ,"date":data[i][0][0:10]}
            content_all.append(data[i][5])
        if data[i][0][0:10]<time_range:
            break

        ptt.append(temp)


    #日期範圍
    time_range=datetime.datetime.now()+datetime.timedelta(days=-5)
    time_range=time_range.strftime("%Y%m%d")

    #拿 google 資料
    db =  sqlite3.connect('stock.db')
    cursor = db.execute("SELECT * from Google_NEWS where Title like ? ", ('%{}%'.format(search),))
    data=cursor.fetchall()
    db.close()


    google=[]
    for i in range(len(data)-1,1,-1):
        if str(data[i][0])>time_range:
            temp = {'value':data[i][3]\
                        #,'final_update':data[i].final_update\
                        ,'link':data[i][4]\
                        ,"date":data[i][0]}

            content_all.append(data[i][5])
            #content_all_date.append(data[i][0])
        if str(data[i][0])<time_range:

            break

        google.append(temp)




    # #日期範圍
    # time_range=datetime.datetime.now()+datetime.timedelta(days=-14)
    # time_range=time_range.strftime("%Y-%m-%d")

    #拿 yahoo 資料
    db =  sqlite3.connect('stock.db')
    cursor = db.execute("SELECT * from Yahoo_NEWS where Title like ? ", ('%{}%'.format(search),))
    data=cursor.fetchall()
    db.close()

    yahoo=[]
    for i in range(len(data)-1,1,-1):
        if str(data[i][0])>time_range:
            temp = {'value':data[i][3]\
                        #,'final_update':data[i].final_update\
                        ,'link':data[i][5]\
                        ,"date":data[i][0]}
            # content_all.append(data[i][4])
        if str(data[i][0])<time_range:
            break

        yahoo.append(temp)

    #print(yahoo)
    if len(google)<1:
        google="false"
    if len(yahoo)<1:
        yahoo="false"
    if len(ptt)<1:
        ptt="false"


    pos_count=0
    neg_count=0
    this_paper_pos=0
    this_paper_neg=0

    for i in range(len(content_all)):
        for j in range(len(pos)):
            if pos[j] in str(content_all[i]):
                #print(time_range,content_all_date[i],(int(content_all_date[i])-int(time_range)))
                this_paper_pos=this_paper_pos+1
        for j in range(len(neg)):
            if neg[j] in str(content_all[i]):
                this_paper_neg=this_paper_neg+1

        if this_paper_pos >this_paper_neg: 
            pos_count=pos_count+1
        else:
            neg_count=neg_count+1
        this_paper_pos=0
        this_paper_neg=0


    
    neg_score= ((neg_count)/(pos_count+neg_count))*100
    pos_score= ((pos_count)/(pos_count+neg_count))*100

    if neg_score>pos_score:
        score=pos_score
    else:
        score=neg_score

    print("score",neg_score,pos_score)


    news={"google":google,"yahoo":yahoo,"ptt":ptt}
    dict_final={"news":news,"emotionValue": round(score)}
    return Response(dict_final)


@api_view(['GET'])
def sentiment_score(request,search):
    search = request.query_params.get('search', None)

    pos,neg=sent_dict()
    #pos,neg=fin_dict()
    #pos,neg=sent_dict()
    #日期範圍
    time_range=datetime.datetime.now()+datetime.timedelta(days=-14)
    time_range=time_range.strftime("%Y-%m-%d")
    db =  sqlite3.connect('stock.db')
    cursor = db.execute("SELECT * from PTT_NEWS where title like ? ", ('%{}%'.format(search),))
    data=cursor.fetchall()
    db.close()
    #print(data[0][0])
    data_all=[]
    content_all=[]
    href_all=[]
    title_all=[]
    date_all=[]
    for i in range(len(data)-1,1,-1):
        if data[i][0][0:10]>time_range:
            #data_all.append(data[i])  
            content_all.append(data[i][5])
            href_all.append(data[i][3])
            title_all.append(data[i][2])
            date_all.append(data[i][0][0:10])
        if data[i][0][0:10]<time_range:
            break


    #日期範圍
    time_range=datetime.datetime.now()+datetime.timedelta(days=-14)
    time_range=time_range.strftime("%Y%m%d")

    #拿 google 資料
    db =  sqlite3.connect('stock.db')
    cursor = db.execute("SELECT * from Google_NEWS where Title like ? ", ('%{}%'.format(search),))
    data=cursor.fetchall()
    db.close()
    #print(data[0][0])
    google=[]
    for i in range(len(data)-1,1,-1):
        if str(data[i][0])>time_range:
            #data_all.append(data[i])  
            content_all.append(data[i][5])
            href_all.append(data[i][4])
            title_all.append(data[i][3])
            date_all.append(data[i][0])
        if str(data[i][0])<time_range:
            break

    #拿取正向  負向自詞
    positiveValue=[]
    positiveNews=[]
    negativeValue=[]
    negativeNews=[]
    pos_count=0
    neg_count=0
    allpos=[]
    allneg=[]


    for i in range(len(content_all)):
        for j in range(len(pos)):
            if pos[j] in str(content_all[i]):
                temp = {'value':title_all[i],'link':href_all[i],"date":date_all[i]}
                pos_count=pos_count+1
                allpos.append(pos[j])

        for j in range(len(neg)):
            if neg[j] in str(content_all[i]):
                temp = {'value':title_all[i],'link':href_all[i],"date":date_all[i]}
                neg_count=neg_count+1
                allneg.append(neg[j])

        if pos_count >neg_count: 
            positiveNews.append(temp)
            pos_count=0
            neg_count=0
        elif neg_count >pos_count:
            negativeNews.append(temp)
            pos_count=0
            neg_count=0




    #把文字數量算出來
    #正面
    l1 = allpos
    set01 = set(l1)
    dict01 = {item: l1.count(item) for item in set01}
    sorted_x = sorted(dict01.items(), key=lambda x: x[1], reverse=True)
    #排序
    for i in range(len(sorted_x)):
        temp={"text":sorted_x[i][0],"value":sorted_x[i][1]}
        positiveValue.append(temp)

    #負面
    l1 = allneg
    set01 = set(l1)
    dict01 = {item: l1.count(item) for item in set01}
    sorted_x = sorted(dict01.items(), key=lambda x: x[1], reverse=True)
    #排序
    for i in range(len(sorted_x)):
        temp={"text":sorted_x[i][0],"value":sorted_x[i][1]}
        negativeValue.append(temp)

    if len(positiveValue)<1:
        positiveValue="false"
    if len(positiveNews)<1:
        positiveNews="false"
    if len(negativeNews)<1:
        negativeNews="false"
    if len(negativeValue)<1:
        negativeValue="false"


    chartBar={"positiveValue":positiveValue,"positiveNews":positiveNews,"negativeValue":negativeValue,"negativeNews":negativeNews}
    final={"chartBar":chartBar}

    return Response(final)












from rest_framework import status
@api_view(['GET'])
def find_house_data(request):
    year = request.GET.get('year', "108")
    season = request.GET.get('season', "2")



    #   面試的專案

    import sys
    import requests
    from zipfile import ZipFile
    import pandas as pd
    import json

    # 爬蟲function
    def download_file(url, fileName):
        r = requests.get(url, stream=True)
        if r.status_code == 200: # HTTP 200 OK
            if r.headers['Content-Type'] == 'application/octet-stream': # zip檔串流
                size = r.headers['Content-Length'] # zip檔大小
                print('file size: {} bytes'.format(size))   #觀看檔案大小

                # 執行下載過程
                with open(fileName, 'wb') as f: # 在本地路徑開檔
                    count = 0
                    for chunk in r.iter_content(chunk_size=1024):  # 緩衝下載
                        if chunk: # 過濾掉保持活躍的新塊
                            f.write(chunk) # 寫入
                            # 計算下載進度
                            count += len(chunk)
                            #print('{}: {:3d}%'.format(fileName, int(count / int(size) * 100)))    #可以觀看下載進度
                        else:
                            print('no chunk')
                r.close() # 關閉 Response
                return fileName
            else:
                print('content type is not zip file.')
                r.close() # 關閉 Response
                return None
        else:
            print('request failed')
            r.close() # 關閉 Response
            return None
    #中文 跟阿拉伯數字轉換    
    number_map = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9
    }

    #爬蟲   輸入年份   (題目指定是108S2)
    # year=input("你要哪一個年份的資料 (民國)")
    # season=input("你要哪一季的資料  輸入數字 1~4")
    url="http://plvr.land.moi.gov.tw/DownloadSeason?season="+year+"S"+season+"&type=zip&fileName=lvr_landcsv.zip"
    download_file(url, year+"S"+season+".zip")

    # # 輸入想要看的數據資料    # 題目預設為   主要用途為 (住家用) 建物型態為  (住宅大樓)    樓層在13樓以上
    # how_to_use=input("你想查的房子 主要用途為?  (住家用,商業用,工業用,停車用....)")
    # house_type=input("你想查的房子 建物型態為?  (住宅大樓,套房,公寓....)")
    # house_level=input("你想查的房子 總樓層數希望大於等於幾層樓?  輸入阿拉伯數字 5,6,10....")

    how_to_use="住家用"
    house_type="住宅大樓"
    house_level="13"


    #開啟要跑的縣市    可寫轉換   題目指定為【臺北市/新北市/桃園市/臺中市/高雄市】的【不動產買賣】資料。
    city_list=["臺北市","新北市","桃園市","臺中市","高雄市"]
    city_list2=["a","f","h","b","e"]
    all_city_json=[]
    for city_var in range(len(city_list)):

        myzip=ZipFile(year+"S"+season+".zip")
        f=myzip.open(city_list2[city_var]+'_lvr_land_a.csv')
        df=pd.read_csv(f, encoding='utf-8')  
        #print(df)
        f.close()
        myzip.close()



        # 把中文的樓層  轉成數字
        level=df["總樓層數"].tolist()
        for i in range(len(level)):
            try:
                level[i]=level[i].replace("層","")
                if len(level[i])==1:
                    level[i]=number_map[level[i]]
                elif len(level[i])==2:
                    level[i]=10+number_map[level[i][1]]
                elif len(level[i])==3:
                    level[i]=(number_map[level[i][0]])*10+number_map[level[i][2]]
            except:
                level[i]=0
        level[0]=0
        df["換算後的樓層數"]=level




        #根據剛剛輸入的資料   把資料篩選出來
        mask = (df["主要用途"]==how_to_use) & (df["建物型態"].str.contains(house_type)) & (df["換算後的樓層數"]>=int(house_level))  #篩選條件
        cols = ['交易年月日',"鄉鎮市區",'主要用途','建物型態','總樓層數']  #提取名稱、價格、分類欄位
        #print(df.loc[mask,cols].head(10))
        df_new=df.loc[mask,cols]


        #把json 黨輸出出來

        df_new['交易年月日']=df_new[['交易年月日']].astype(str)
        date_data=df_new["交易年月日"].tolist()
        date_data2=list(set(date_data))
        date_data2=sorted(date_data2)
        time_slots=[]
        for i in range(len(date_data2)):
            mask = (df_new["交易年月日"]==date_data2[i])  #篩選條件
            cols = ['交易年月日',"鄉鎮市區",'建物型態']  #提取名稱、價格、分類欄位
            df_temp=df_new.loc[mask,cols]
            events=[]
            date=date_data2[i]
            for j in range(len(df_temp)):

                district=df_temp["鄉鎮市區"].tolist()[j]
                building_state=df_temp["建物型態"].tolist()[j]

                events_dict={"district":district,"building_state":building_state}
                events.append(events_dict)
            dict_temp={"date":date,"events":events}
            time_slots.append(dict_temp)
        final={"city":city_list[city_var],"time_slots":time_slots}
        all_city_json.append(final)

    print("輸出成功")
    return Response(all_city_json, status=status.HTTP_201_CREATED)






#歷史資訊

@api_view(['GET'])
def technihistory2(request):

    date = request.GET.get('date', "2024-03")


    dict_finalt={'board':"", 'final_update':"",'tableData':""}
    if request.method == 'GET':
#        data = technicHistory.objects.all()
        data = technicHistory.objects.filter((Q(start_date__icontains=date)))


        tableData=[]
        total_return=0
        total_start_price=0
        total_final_price=0


        for i in range(len(data)):
            dict = {'id':data[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':data[i].stock_name,'start_date':data[i].start_date\
                        ,'start_price':data[i].buy_price\
                        ,'over_date':data[i].over_date\
                        ,'current_price':data[i].sell_price\
                        ,'now_return':str(round(float(data[i].return_value),2))\
                        ,'type':data[i].type\
                            }
            tableData.append(dict)
            total_return=total_return+float(data[i].return_value)
            total_return=round(total_return,2)
            total_start_price=total_start_price+float(data[i].buy_price)
            total_final_price=total_final_price+float(data[i].sell_price)

        a=round(((total_final_price-total_start_price)/total_start_price)*100,2)

        board= {"today": 'X',"total":str(a)}
        dict_finalt={'board':board, 'final_update':date,'tableData':tableData}
        return Response(dict_finalt)