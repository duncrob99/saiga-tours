"""travel_website URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from main.sitemaps import (TourSitemap,
                           PageSitemap,
                           ArticleSitemap,
                           DetailsSitemap,
                           RegionToursMap,
                           RegionGuidesMap,
                           DestinationToursMap,
                           DestinationGuidesMap,
                           StaticPagesMap)

from customers import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('stats/', include('analytics.urls')),
    path('sitemap.xml',
         sitemap,
         {'sitemaps': {
             'tours': TourSitemap,
             'pages': PageSitemap,
             'articles': ArticleSitemap,
             'details': DetailsSitemap,
             'regiontours': RegionToursMap,
             'regionguides': RegionGuidesMap,
             'destinationtours': DestinationToursMap,
             'destinationguides': DestinationGuidesMap,
             'static': StaticPagesMap
         }},
         name='django.contrib.sitemaps.views.sitemap'),
    path('silk/', include('silk.urls', namespace='silk')),
    path('media/form_files/<uuid:user_id>/<uuid:form_id>/<str:filename>/', views.form_file, name='form_file'),
    path('customers/', include('customers.urls')),
    path('', include('main.urls'))
]


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'main.views.error_404'
handler500 = 'main.views.error_500'
