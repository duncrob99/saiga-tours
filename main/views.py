from datetime import datetime

import ngram
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect

from .forms import *
from .models import *


def assert_visible(request, model: DraftHistory):
    if not (model.published or request.user.is_staff):
        raise Http404


# Create your views here.
def front_page(request):
    context = {
                  'tours': Tour.visible(request.user.is_staff),
                  'banners': BannerPhoto.objects.filter(active=True).order_by('?'),
              } | global_context(request)
    return render(request, 'main/front-page.html', context)


def global_context(request):
    context = {
        'regions': Region.visible(request.user.is_staff),
        'pages': Page.visible(request.user.is_staff).filter(parent=None),
        'settings': Settings.load(),
        'subscription_form': SubscriptionForm()
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
              } | global_context(request)

    return render(request, 'main/destination.html', context)


def destination_details(request, region_slug, country_slug, detail_slug):
    details = get_object_or_404(DestinationDetails,
                                destination__region__slug=region_slug,
                                destination__slug=country_slug,
                                slug=detail_slug)

    assert_visible(request, details)

    context = {
                  'details': details
              } | global_context(request)

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
              } | global_context(request)
    return render(request, 'main/tour.html', context)


def tours(request):
    context = {
                  'tours': Tour.visible(request.user.is_staff),
                  'destinations': Destination.visible(request.user.is_staff)
              } | global_context(request)
    return render(request, 'main/tours.html', context)


def article(request, slug):
    article_obj = get_object_or_404(Article, slug=slug)
    assert_visible(request, article_obj)

    context = {
                  'article': article_obj
              } | global_context(request)
    return render(request, 'main/article.html', context)


def article_list(request, type, title):
    articles = Article.visible(request.user.is_staff).filter(type=type)

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    if start_date != '' and start_date is not None:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        articles = articles.filter(creation__gte=start_date)
    if end_date != '' and end_date is not None:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        articles = articles.filter(creation__lte=end_date)

    tags = Tag.objects.filter(articles__type=type)
    for tag in tags:
        if request.GET.get(f'tag-{tag.slug}') is not None:
            print('Filtering by ' + tag.name)
            articles = articles.filter(tags__pk=tag.pk)

    query = request.GET.get('q')
    if query is not None and query != '':
        article_ngrams = ngram.NGram(articles, key=lambda article: ' '.join(
            (article.title.lower(), article.keywords.lower(), article.tag_list().lower())), N=4, warp=2)
        search_results = article_ngrams.search(query.lower())
        print(search_results)
        articles = [result[0] for result in sorted(search_results, key=lambda result: result[1], reverse=True)]

    paginator = Paginator(articles, 25)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
                  'title': title,
                  'page_obj': page_obj,
                  'destinations': Destination.visible(request.user.is_staff),
                  'tags': tags,
                  'query': query or '',
                  'start_date': start_date or '',
                  'end_date': end_date or ''
              } | global_context(request)
    return render(request, 'main/article_list.html', context)


def news(request):
    return article_list(request, Article.NEWS, "News Articles")


def blog(request):
    return article_list(request, Article.BLOG, "Blog Posts")


def region(request, slug):
    region_obj = get_object_or_404(Region, slug=slug)
    tours_list = Tour.visible(request.user.is_staff).filter(destinations__region=region_obj).distinct()
    destination_list = Destination.visible(request.user.is_staff).filter(region=region_obj)

    assert_visible(request, region_obj)

    context = {
                  'region': region_obj,
                  'destinations': destination_list,
                  'tours': tours_list
              } | global_context(request)
    return render(request, 'main/region.html', context)


def page(request, path):
    page_obj = Page.reverse_path(path)
    assert_visible(request, page_obj)

    context = {
                  'page': page_obj
              } | global_context(request)
    return render(request, 'main/page.html', context)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        from_email = form.cleaned_data['from_email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        try:
            send_mail(f'Contact form submission: "{subject}"',
                      f'From: {from_email}\nSubject: {subject}\nMessage: \n{message}', from_email,
                      [Settings.load().contact_form_email])
            ContactSubmission.objects.create(from_email=from_email, subject=subject, message=message)
            messages.add_message(request, messages.SUCCESS, 'Successfully sent')
            return redirect('front-page')
        except BadHeaderError:
            form.add_error('from_email', 'Invalid header found.')
            ContactSubmission.objects.create(from_email=from_email, subject=subject, message=message, success=False)
            return render(request, 'main/contact.html', {'form': form} | global_context(request))
    return render(request, 'main/contact.html', {'form': form} | global_context(request))


def subscribe(request, return_path: str = None):
    form = SubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            SubscriptionSubmission.objects.create(email_address=form.cleaned_data['email'])
            messages.add_message(request, messages.SUCCESS, 'Successfully subscribed')
        except IntegrityError:
            messages.add_message(request, messages.WARNING, 'Already subscribed')
    else:
        messages.add_message(request, messages.WARNING, 'Invalid attempt to subscribe')
    if return_path is not None:
        return HttpResponseRedirect(return_path)
    else:
        return redirect('front-page')
