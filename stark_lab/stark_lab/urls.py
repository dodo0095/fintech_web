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
    path('watchCenter.html', TemplateView.as_view(template_name="watchCenter.html")),
    #path('chose_robot/', views.chose_robot),
    path('api/', include(router.urls)),


    #現在的選股
    url(r'^api/basicCurrent/',views.basicCurrentapi2),
    url(r'^api/technicCurrent/',views.technicCurrentapi2),

    #過去的選股
    url(r'^api/technihistory/',views.technihistory2),


    #新增跟刪除的選股
    url(r'^api/add_and_delete_list/',views.add_and_delete_list),
    url(r'^api/add_and_delete_list2/',views.add_and_delete_list2),



    url(r'^api/news_get/(?P<search>)$',views.news_get),
    url(r'^api/sentiment_score/(?P<search>)$',views.sentiment_score),

    url(r'^find_house_data/',views.find_house_data),


    url(r'^chart/',views.chart_view),
    url(r'^chart_2/',views.chart_view_2),

    url(r'^data_to_chart_2/',views.data_to_chart_2),

    path('api/performances/', views.monthly_performance_api, name='performance_api'),


]
