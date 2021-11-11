from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404

from .models import *


# Create your views here.
def front_page(request):
    context = navbar_context()
    return render(request, 'main/front-page.html', context)


def navbar_context():
    context = {
        'regions': Region.objects.all()
    }
    return context


def destination_overview(request, region, country):
    destination = get_object_or_404(Destination, region__slug=region, slug=country)

    context = {
                  'destination': destination
              } | navbar_context()

    return render(request, 'main/destination.html', context)


def destination_details(request, region, country, detail):
    details = get_object_or_404(DestinationDetails, destination__region__slug=region, destination__slug=country,
                                slug=detail)

    context = {
                  'details': details
              } | navbar_context()

    return render(request, 'main/destination_details.html', context)


def navbar(request):
    context = {
        'regions': Region.objects.all()
    }
    return render(request, 'main/navbar.html', context)


def tour(request, slug):
    context = {
                  'tour': Tour.objects.get(slug=slug)
              } | navbar_context()
    return render(request, 'main/tour.html', context)


def tours(request):
    context = {
                  'tours': Tour.objects.all(),
                  'destinations': Destination.objects.all()
              } | navbar_context()
    return render(request, 'main/tours.html', context)


def article(request, slug):
    context = {
                  'article': Article.objects.get(slug=slug)
              } | navbar_context()
    return render(request, 'main/article.html', context)


def news(request):
    news_list = Article.objects.filter(type=Article.NEWS)
    paginator = Paginator(news_list, 25)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    context = {
                  'page_obj': page_obj
              } | navbar_context()
    return render(request, 'main/news.html', context)


def region(request, slug):
    region = get_object_or_404(Region, slug=slug)
    tours = Tour.objects.filter(destinations__region=region).distinct()
    print(tours)
    context = {
                  'region': region,
                  'tours': tours
              } | navbar_context()
    return render(request, 'main/region.html', context)
