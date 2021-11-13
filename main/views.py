from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render, get_object_or_404

from .models import *


def assert_visible(request, model: DraftHistory):
    if not (model.published or request.user.is_staff):
        raise Http404


# Create your views here.
def front_page(request):
    context = {
                  'tours': Tour.visible(request.user.is_staff)
              } | navbar_context(request)
    return render(request, 'main/front-page.html', context)


def navbar_context(request):
    context = {
        'regions': Region.visible(request.user.is_staff),
        'pages': Page.visible(request.user.is_staff).filter(parent=None)
    }
    return context


def destination_overview(request, region_slug, country_slug):
    destination = get_object_or_404(Destination, region__slug=region_slug, slug=country_slug)
    detail_list = destination.details.visible(request.user.is_staff)
    tour_list = destination.tours.visible(request.user.is_staff)

    assert_visible(request, destination)

    context = {
                  'destination': destination,
                  'details': detail_list,
                  'tours': tour_list
              } | navbar_context(request)

    return render(request, 'main/destination.html', context)


def destination_details(request, region_slug, country_slug, detail_slug):
    details = get_object_or_404(DestinationDetails,
                                destination__region__slug=region_slug,
                                destination__slug=country_slug,
                                slug=detail_slug)

    assert_visible(request, details)

    context = {
                  'details': details
              } | navbar_context(request)

    return render(request, 'main/destination_details.html', context)


# Just to get type hinting, not actually needed
def navbar(request):
    context = {
        'regions': Region.visible(request.user.is_staff),
        'pages': Page.visible(request.user.is_staff).filter(parent=None)
    }
    return render(request, 'main/navbar.html', context)


def tour(request, slug):
    tour_obj = get_object_or_404(Tour, slug=slug)
    assert_visible(request, tour_obj)

    context = {
                  'tour': tour_obj
              } | navbar_context(request)
    return render(request, 'main/tour.html', context)


def tours(request):
    context = {
                  'tours': Tour.visible(request.user.is_staff),
                  'destinations': Destination.visible(request.user.is_staff)
              } | navbar_context(request)
    return render(request, 'main/tours.html', context)


def article(request, slug):
    article_obj = get_object_or_404(Article, slug=slug)
    assert_visible(request, article_obj)

    context = {
                  'article': article_obj
              } | navbar_context(request)
    return render(request, 'main/article.html', context)


def news(request):
    news_list = Article.visible(request.user.is_staff).filter(type=Article.NEWS)
    paginator = Paginator(news_list, 25)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    context = {
                  'title': "News Articles",
                  'page_obj': page_obj
              } | navbar_context(request)
    return render(request, 'main/article_list.html', context)


def blog(request):
    post_list = Article.visible(request.user.is_staff).filter(type=Article.BLOG)
    paginator = Paginator(post_list, 25)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    context = {
                  'title': 'Blog Posts',
                  'page_obj': page_obj
              } | navbar_context(request)

    return render(request, 'main/article_list.html', context)


def region(request, slug):
    region_obj = get_object_or_404(Region, slug=slug)
    tours_list = Tour.visible(request.user.is_staff).filter(destinations__region=region_obj).distinct()
    destination_list = Destination.visible(request.user.is_staff).filter(region=region_obj)

    assert_visible(request, region_obj)

    context = {
                  'region': region_obj,
                  'destinations': destination_list,
                  'tours': tours_list
              } | navbar_context(request)
    return render(request, 'main/region.html', context)


def page(request, path):
    page_obj = Page.reverse_path(path)
    assert_visible(request, page_obj)

    context = {
                  'page': page_obj
              } | navbar_context(request)
    return render(request, 'main/page.html', context)
