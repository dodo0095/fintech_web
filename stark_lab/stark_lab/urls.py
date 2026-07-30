from django.urls import path, include
from rest_framework import routers
from apiserver import views
from django.views.generic import TemplateView

router = routers.DefaultRouter()
router.register(r'chose_robot', views.chose_robot, basename='chose_robot')
router.register(r'technicHistory', views.technicHistoryapi, basename='technicHistory')
router.register(r'basicHistory', views.basicHistoryapi, basename='basicHistory')
router.register(r'articleapi', views.articleapi, basename='articleapi')
router.register(r'articleapi2', views.articleapi2, basename='articleapi2')

handler404 = 'apiserver.views.custom_page_not_found'
handler500 = 'apiserver.views.custom_server_error'

urlpatterns = [
    path('', TemplateView.as_view(template_name="index.html")),
    path('index.html', TemplateView.as_view(template_name="index.html")),
    # path('bot.html', TemplateView.as_view(template_name="bot.html")),
    path('botBlog.html', TemplateView.as_view(template_name="botBlog.html")),
    # path('botAbout.html', TemplateView.as_view(template_name="botAbout.html")),
    path('botBasicHistory.html', TemplateView.as_view(template_name="botBasicHistory.html")),
    path('botBasicCurrent.html', TemplateView.as_view(template_name="botBasicCurrent.html")),
    path('botTechnicHistory.html', TemplateView.as_view(template_name="botTechnicHistory.html")),
    path('botTechnicCurrent.html', TemplateView.as_view(template_name="botTechnicCurrent.html")),
    # path('watchCenter.html', TemplateView.as_view(template_name="watchCenter.html")),

    path('api/', include(router.urls)),

    # 現在的選股
    path('api/basicCurrent/', views.basicCurrentapi2),
    path('api/technicCurrent/', views.technicCurrentapi2),

    # 過去的選股
    path('api/technihistory/', views.technihistory2),

    # 新增跟刪除的選股
    path('api/add_and_delete_list/', views.add_and_delete_list),
    path('api/add_and_delete_list2/', views.add_and_delete_list2),

    path('chart/', views.chart_view),
    path('chart_2/', views.chart_view_2),
    path('data_to_chart_2/', views.data_to_chart_2),

    path('api/performances/', views.monthly_performance_api, name='performance_api'),
]
