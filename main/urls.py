from django.urls import path

from . import views

urlpatterns = [
    path('', views.front_page, name='front-page'),
    path('destination/<slug:region>/<slug:country>/', views.destination_overview, name='destination'),
    path('details/<slug:region>/<slug:country>/<slug:detail>/', views.destination_details, name='destination-details'),
    path('tours/', views.tours, name='tours'),
    path('tour/<slug:slug>', views.tour, name='tour'),
    path('article/<slug:slug>', views.article, name='article'),
    path('news/', views.news, name='news'),
    path('region/<slug:slug>', views.region, name='region')
]
