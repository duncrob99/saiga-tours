from django.urls import path

from . import views

urlpatterns = [
    # path('', views.front_page, name='front-page'),
    # path('contact/', views.contact, name='contact'),
    # path('subscribe/', views.subscribe, name='subscribe'),
    # path('subscribe/<path:return_path>', views.subscribe, name='subscribe'),
    #
    # path('destinations/', views.destinations, name='destinations'),
    # path('region/<slug:slug>', views.region, name='region'),
    # path('destination/<slug:region_slug>/<slug:country_slug>/', views.destination_overview, name='destination'),
    # path('details/<slug:region_slug>/<slug:country_slug>/<slug:detail_slug>/', views.destination_details,
    #      name='destination-details'),
    #
    # path('tours/', views.tours, name='tours'),
    # path('tour/<slug:slug>', views.tour, name='tour'),
    # path('tours/<slug:region_slug>/', views.region_tours, name='tours'),
    # path('tours/<slug:region_slug>/<slug:country_slug>/', views.country_tours, name='tours'),
    # path('tours/<slug:region_slug>/<slug:country_slug>/<slug:detail_slug>/', views.country_tours_info, name='tours'),
    #
    # path('article/<slug:slug>', views.article, name='article'),
    # path('news/', views.news, name='news'),
    # path('blog/', views.blog, name='blog'),
    #
    # path('favicon.ico', views.favicon, name='favicon'),
    #
    # path('<path:path>', views.page, name='page')
    path('', views.statistics, name='statistics'),
    path('view/', views.view, name='view'),
    path('heartbeat/', views.heartbeat, name='heartbeat'),
    path('close/', views.close_view, name='close'),
    path('mouse-action/', views.mouse_action, name='mouse-action'),
    path('accept-cookies/', views.accept_cookies, name='accept-cookies'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('subscribe/<path:return_path>/', views.subscribe, name='subscribe'),
]
