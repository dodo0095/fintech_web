from django.urls import path

from . import views

app_name = "twbacktest"

urlpatterns = [
    path("", views.index, name="index"),
    path("chart/<str:strategy>/", views.equity_chart, name="chart"),
]
