from django.shortcuts import render
# Create your views here.
from rest_framework import viewsets
from apiserver.serializers import  bot_apiSerializer,technicHistory_Serializer,technicCurrent_Serializer
from apiserver.serializers import basicHistory_Serializer,basicCurrent_Serializer,article_Serializer,article2_Serializer,MonthlyPerformance_Serializer
from apiserver.models import bot,technicHistory,technicCurrent,basicHistory,basicCurrent,article_1,article_2,MonthlyPerformance
from rest_framework import generics
import django_filters.rest_framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime
from django.db.models import Q
#from apiserver.update import *



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



















#歷史資訊

@api_view(['GET'])
def technihistory2(request):

    date = request.GET.get('date', "2024-03")


    dict_finalt={'board':"", 'final_update':"",'tableData':""}
    if request.method == 'GET':
        data = technicHistory.objects.all()
        #data = technicHistory.objects.filter((Q(start_date__icontains=date)))


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

        #a=round(((total_final_price-total_start_price)/total_start_price)*100,2)
        if total_start_price and total_start_price != 0:
            a = round(((total_final_price - total_start_price) / total_start_price) * 100, 2)
        else:
        # 依你的 API 設計選擇合適的回應方式
            a = None  # 或 0，或直接回傳錯誤訊息給前端
        # logger.warning(f"total_start_price is zero/None for request params: {request.query_params}")



        board= {"today": 'X',"total":str(a)}
        dict_finalt={'board':board, 'final_update':date,'tableData':tableData}
        return Response(dict_finalt)





@api_view(['GET'])
def add_and_delete_list(request):


    dict_finalt={'add_list':"", 'delete_list':"","keep_list":""}
    if request.method == 'GET':
        Current_list = basicCurrent.objects.all().values_list('stock_name', flat=True)
        History_list = basicHistory.objects.all().order_by('-id')[:20].values_list('stock_name', flat=True)
        print(Current_list)
        print(History_list)

        add_list=[]
        delete_list=[]
        keep_list=[]
        for i in range(len(Current_list)):

            if Current_list[i] in History_list :
                #print(Current_list[i]," keep")
                keep_list.append(Current_list[i])
            else:
                #print("新增",Current_list[i])
                add_list.append(Current_list[i])


        for i in range(len(History_list)):

            if History_list[i] in Current_list :
                pass    
            else:
                #print("no")
                delete_list.append(History_list[i])

        print(len(add_list),len(delete_list))
        print(keep_list)
        dict_finalt={'add_list':add_list, 'delete_list':delete_list,"keep_list":keep_list}
        return Response(dict_finalt)





@api_view(['GET'])
def add_and_delete_list2(request):


    dict_finalt={'add_list':"", 'delete_list':"","keep_list":""}
    if request.method == 'GET':
        
        Current_list_2 = basicCurrent.objects.all().values_list('stock_name', flat=True)
        History_list_2 = basicHistory.objects.all().order_by('-id')[:20].values_list('stock_name', flat=True)


        Current_list = basicCurrent.objects.all()
        History_list = basicHistory.objects.all().order_by('-id')[:20]
        #print(Current_list[0].stock_name)
        #print(History_list)

        add_list=[]
        delete_list=[]
        keep_list=[]
        for i in range(len(Current_list)):
            #print(Current_list[i].stock_name," keep")
            if Current_list_2[i] in History_list_2 :
                print(Current_list[i].stock_name," keep")
                
            else:
                #print("新增",Current_list[i])
            
                dict_temp = {'id':Current_list[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':Current_list[i].stock_name,'start_date':Current_list[i].start_date\
                        ,'start_price':Current_list[i].start_price\
                        ,'over_date':Current_list[i].over_date\
                        ,'current_price':Current_list[i].current_price\
                        ,'now_return':str(round(float(Current_list[i].now_return),2))\
                        ,'type':Current_list[i].type\
                            }
                add_list.append(dict_temp)


        for i in range(len(History_list)):

            if History_list_2[i] in Current_list_2 :
                dict_temp = {'id':History_list[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':History_list[i].stock_name,'start_date':History_list[i].start_date\
                        ,'start_price':History_list[i].buy_price\
                        ,'over_date':History_list[i].over_date\
                        ,'current_price':History_list[i].sell_price\
                        ,'now_return':str(round(float(History_list[i].return_value),2))\
                        ,'type':History_list[i].type\
                            }
                keep_list.append(dict_temp)
                #print(History_list[i].stock_name," keep")    
            else:
                #print("no")
                dict_temp = {'id':History_list[i].id\
                        #,'final_update':data[i].final_update\
                        ,'stock_name':History_list[i].stock_name,'start_date':History_list[i].start_date\
                        ,'start_price':History_list[i].buy_price\
                        ,'over_date':History_list[i].over_date\
                        ,'current_price':History_list[i].sell_price\
                        ,'now_return':str(round(float(History_list[i].return_value),2))\
                        ,'type':History_list[i].type\
                            }
                delete_list.append(dict_temp)



        #print(len(add_list),len(delete_list))
        dict_finalt={'add_list':add_list, 'delete_list':delete_list,"keep_list":keep_list}
        return Response(dict_finalt)




def chart_view(request):
    # 傳遞數據到模板
    return render(request, 'chart.html')



def chart_view_2(request):
    # 傳遞數據到模板
    
    return render(request, 'chart-1.html')


@api_view(['GET'])
def data_to_chart_2(request):
    # 傳遞數據到模板
    price = [1, 10, 18, 18, 25]
    date=['2024-1月', '2024-2月', '2024-3月', '2024-4月', '2024-5月']

    dict_finalt={'price':price,'date':date}
    return Response(dict_finalt)



@api_view(['GET'])
def monthly_performance_api(request):
    data = MonthlyPerformance.objects.all().order_by('label')
    serializer = MonthlyPerformance_Serializer(data, many=True)
    return Response(serializer.data)



from django.shortcuts import render

# 404 要有 exception 參數（可設預設值避免誤呼叫）
def custom_page_not_found(request, exception=None):
    return render(request, '404.html', {'path': request.path}, status=404)

# 500 只能有 request；Django 不會傳 exception 進來
def custom_server_error(request):
    return render(request, '404.html', status=500)
