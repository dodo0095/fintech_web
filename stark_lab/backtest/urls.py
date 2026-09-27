from django.urls import path

from . import views

app_name = "backtest"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/search", views.api_search, name="search"),
    path("api/run", views.api_run, name="run"),
]
