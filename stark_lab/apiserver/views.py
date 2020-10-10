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
        queryset = article_1.objects.all()
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
        queryset = article_2.objects.all()
        username = self.request.query_params.get('title', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(title=str(title))
        return queryset