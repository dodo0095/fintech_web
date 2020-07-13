"""stark_lab URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include, path
from rest_framework import routers
from apiserver import views
from django.conf.urls import url
from django.views.generic import TemplateView


router = routers.DefaultRouter()
router.register(r'chose_robot', views.chose_robot, basename='chose_robot')
router.register(r'history_stock', views.history_stock, basename='history_stock')
router.register(r'now_chose_stock', views.now_chose_stock, basename='now_chose_stock')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('bot.html', TemplateView.as_view(template_name="bot.html")),
    path('botBasicHistory.html', TemplateView.as_view(template_name="botBasicHistory.html")),
    path('botBasicCurrent.html', TemplateView.as_view(template_name="botBasicCurrent.html")),
    path('botTechnicHistory.html', TemplateView.as_view(template_name="botTechnicHistory.html")),
    path('botTechnicCurrent.html', TemplateView.as_view(template_name="botTechnicCurrent.html")),
    #path('chose_robot/', views.chose_robot),
    path('', include(router.urls)),
]
