from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.front_page, name='front-page'),
    path('contact/', views.contact, name='contact'),

    path('destinations/', views.destinations, name='destinations'),
    path('region/<slug:slug>', views.region, name='region'),
    path('destination/<slug:region_slug>/<slug:country_slug>/', views.destination_overview, name='destination'),
    path('details/<slug:region_slug>/<slug:country_slug>/<slug:detail_slug>/', views.destination_details,
         name='destination-details'),

    path('tours/', views.tours, name='tours'),
    path('tour/<slug:slug>', views.tour, name='tour'),
    path('tours/<slug:region_slug>/', views.region_tours, name='tours'),
    path('tours/<slug:region_slug>/<slug:country_slug>/', views.country_tours, name='tours'),
    path('tours/<slug:region_slug>/<slug:country_slug>/<slug:detail_slug>/', views.country_tours_info, name='tours'),

    path('create_map/<slug:slug>/', views.create_map, name='create-map'),
    path('copy_map/', views.copy_map, name='copy-map'),

    path('article/<slug:slug>', views.article, name='article'),
    path('news/', views.news, name='news'),
    path('blog/', views.blog, name='blog'),

    path('favicon.ico', views.favicon, name='favicon'),
    # path('resized-image/<str:filename>/<int:width>x<int:height>/', views.resized_imaged, name='resized-image'),
    path('resized-image/<path:filename>/<int:width>x<int:height>/', views.crop_image, name='resized-image'),

    path('doc/<slug:slug>/', views.view_document, name='view-doc'),

    path('edit/position_template/<int:pk>/', views.modify_position_template, name='edit-position-template'),
    path('create/position_template/', views.create_position_template, name='create-position-template'),
    path('create/itinerary_template/', views.create_itinerary_template, name='create-itinerary-template'),

    path('gen_500/', views.gen_500, name='gen-500'),

    path('robots.txt', TemplateView.as_view(template_name='main/robots.txt', content_type='text/plain'), name='robots'),

    path('<path:path>/', views.page, name='page')
]
