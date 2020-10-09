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
router.register(r'technicHistory', views.technicHistoryapi, basename='technicHistory')
#router.register(r'technicCurrent', views.technicCurrentapi, basename='technicCurrent')
router.register(r'basicHistory', views.basicHistoryapi, basename='basicHistory')
#router.register(r'basicCurrent', views.basicCurrentapi, basename='basicCurrent')
router.register(r'articleapi', views.articleapi, basename='articleapi')
router.register(r'articleapi2', views.articleapi2, basename='articleapi2')


urlpatterns = [
    path('admin/', admin.site.urls),
    #path('', TemplateView.as_view(template_name="bot.html")),
    path('bot.html', TemplateView.as_view(template_name="bot.html")),
    path('botBlog.html', TemplateView.as_view(template_name="botBlog.html")),
    path('botAbout.html', TemplateView.as_view(template_name="botAbout.html")),
    path('', TemplateView.as_view(template_name="botAbout.html")),

    path('botBasicHistory.html', TemplateView.as_view(template_name="botBasicHistory.html")),
    path('botBasicCurrent.html', TemplateView.as_view(template_name="botBasicCurrent.html")),


    path('botTechnicHistory.html', TemplateView.as_view(template_name="botTechnicHistory.html")),
    path('botTechnicCurrent.html', TemplateView.as_view(template_name="botTechnicCurrent.html")),
    #path('chose_robot/', views.chose_robot),
    path('api/', include(router.urls)),


    url(r'^api/basicCurrent/',views.basicCurrentapi2),
    url(r'^api/technicCurrent/',views.technicCurrentapi2),

]
