from django.shortcuts import render
# Create your views here.
from rest_framework import viewsets
from apiserver.serializers import  bot_apiSerializer,technicHistory_Serializer,technicCurrent_Serializer
from apiserver.serializers import basicHistory_Serializer,basicCurrent_Serializer
from apiserver.models import bot,technicHistory,technicCurrent,basicHistory,basicCurrent
from rest_framework import generics
import django_filters.rest_framework
from rest_framework.decorators import api_view
from rest_framework.response import Response


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
        queryset = technicHistory.objects.all()
        username = self.request.query_params.get('email', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(email=str(username))
        return queryset




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
        queryset = basicHistory.objects.all()
        username = self.request.query_params.get('email', None)

        #username=urllib.parse.quote(username)


        if username is not None:
            queryset = queryset.filter(email=str(username))
        return queryset




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
