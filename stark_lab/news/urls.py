"""news app 路由，掛在 /api/news/ 之下。"""
from django.urls import path

from news import views

urlpatterns = [
    path("market", views.market),
    path("headlines", views.headlines),
    path("tsmc", views.tsmc),
    path("lookup/<str:code>", views.lookup_code),
    path("stock/<str:code>", views.stock),
    path("fed", views.fed),
    path("heat", views.heat),
    path("events", views.events),
    path("watchlist", views.watchlist),
    path("summary", views.summary),
    path("status", views.status_view),
    path("valuation", views.valuation_default),
    path("valuation/<str:code>", views.valuation_by_code),
]
