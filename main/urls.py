from django.urls import path

from . import views

urlpatterns = [
    path('', views.front_page, name='front-page'),
    path('contact/', views.contact, name='contact'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('subscribe/<str:return_page>', views.subscribe, name='subscribe-with-return'),

    path('region/<slug:slug>', views.region, name='region'),
    path('destination/<slug:region_slug>/<slug:country_slug>/', views.destination_overview, name='destination'),
    path('details/<slug:region_slug>/<slug:country_slug>/<slug:detail_slug>/', views.destination_details,
         name='destination-details'),

    path('tours/', views.tours, name='tours'),
    path('tour/<slug:slug>', views.tour, name='tour'),

    path('article/<slug:slug>', views.article, name='article'),
    path('news/', views.news, name='news'),
    path('blog/', views.blog, name='blog'),

    path('<path:path>', views.page, name='page')
]
