from datetime import datetime
from functools import reduce

import ngram
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.forms import modelform_factory, inlineformset_factory
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
                  'tours': Tour.visible(request.user.is_staff).filter(display=True),
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
    detail_list = destination.details.visible(request.user.is_staff).filter(type=DestinationDetails.GUIDE)
    tour_list = destination.tours.visible(request.user.is_staff).filter(display=True)

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
                                slug=detail_slug, type=DestinationDetails.GUIDE)

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

    extensions = tour_obj.extensions.visible(request.user.is_staff)

    if request.GET.get('parent') is not None:
        parent = Tour.objects.get(slug=request.GET.get('parent'))
        other_extensions = parent.extensions.visible(request.user.is_staff).exclude(pk=tour_obj.pk)
    else:
        other_extensions = None
        parent = None

    if request.user.is_staff:
        form_factory = modelform_factory(Tour, exclude=())
        form = form_factory(request.POST or None, request.FILES or None, instance=tour_obj)
        itinerary_formset_factory = inlineformset_factory(Tour, ItineraryDay, exclude=('tour',), extra=0)
        itinerary_formset = itinerary_formset_factory(request.POST or None, request.FILES or None, instance=tour_obj)
        stops_formset_factory = inlineformset_factory(Tour, Stop, exclude=('tour',), extra=0)
        stops_formset = stops_formset_factory(request.POST or None, instance=tour_obj)
        if request.method == 'POST' and form.is_valid() and itinerary_formset.is_valid() and stops_formset.is_valid():
            form.save()
            itinerary_formset.save()
            stops_formset.save()
        elif request.method == 'POST':
            print(form.errors)
    else:
        form = None
        itinerary_formset = None
        stops_formset = None

    context = {
                  'tour': tour_obj,
                  'form': form,
                  'itinerary_forms': itinerary_formset,
                  'stop_forms': stops_formset,
                  'other_extensions': other_extensions,
                  'parent': parent,
                  'extensions': extensions
              } | global_context(request)
    return render(request, 'main/tour.html', context)


def tours(request):
    context = {
                  'tours': Tour.visible(request.user.is_staff).filter(display=True),
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

    if request.GET.get('author') is not None:
        articles = articles.filter(author__name=request.GET.get('author'))

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    if start_date != '' and start_date is not None:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        articles = articles.filter(creation__gte=start_date)
    if end_date != '' and end_date is not None:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        articles = articles.filter(creation__lte=end_date)

    tags = Tag.objects.filter(articles__type=type)
    checked_tags = []
    for tag in tags:
        if request.GET.get(f'tag-{tag.slug}') is not None:
            articles = articles.filter(tags__pk=tag.pk)
            checked_tags.append(tag.slug)

    checked_authors = []
    for author in Author.visible(request.user.is_staff):
        if request.GET.get(f'author-{author.name}') is not None:
            checked_authors.append(author.name)
    if checked_authors:
        articles = articles.filter(reduce(lambda q, f: q | Q(author__name=f), checked_authors, Q()))

    query = request.GET.get('q')
    if query is not None and query != '':
        article_ngrams = ngram.NGram(articles, key=lambda article: ' '.join(
            (article.title.lower(), article.keywords.lower(), article.tag_list().lower())), N=4, warp=2)
        search_results = article_ngrams.search(query.lower())
        print(search_results)
        articles = [result[0] for result in sorted(search_results, key=lambda result: result[1], reverse=True)]

    paginator = Paginator(articles, Settings.load().articles_per_page)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
                  'title': title,
                  'page_obj': page_obj,
                  'destinations': Destination.visible(request.user.is_staff),
                  'tags': tags,
                  'query': query or '',
                  'start_date': start_date or '',
                  'end_date': end_date or '',
                  'authors': Author.visible(request.user.is_staff),
                  'checked_authors': checked_authors,
                  'checked_tags': checked_tags
              } | global_context(request)
    return render(request, 'main/article_list.html', context)


def news(request):
    return article_list(request, Article.NEWS, "News Articles")


def blog(request):
    return article_list(request, Article.BLOG, "Blog Posts")


def region(request, slug):
    region_obj = get_object_or_404(Region, slug=slug)
    tours_list = Tour.visible(request.user.is_staff).filter(destinations__region=region_obj, display=True).distinct()
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

    if request.user.is_staff:
        form_factory = modelform_factory(Page, exclude=())
        form = form_factory(request.POST or None, request.FILES or None, instance=page_obj)
        if request.method == 'POST' and form.is_valid():
            instance = form.save()
            if 'parent' in form.changed_data or 'slug' in form.changed_data:
                return redirect('page', instance.full_path)
    else:
        form = None

    context = {
                  'page': page_obj,
                  'form': form
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
    elif request.method == 'GET':
        form.fields['subject'].initial = request.GET.get('subject')
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


def destinations(request):
    context = {'destinations': Destination.visible(request.user.is_staff)} | global_context(request)
    return render(request, 'main/destinations.html', context)


def favicon(request):
    return HttpResponseRedirect(Settings.load().logo.url)


def country_tours(request, region_slug, country_slug):
    destination = get_object_or_404(Destination, region__slug=region_slug, slug=country_slug)
    detail_list = destination.details.visible(request.user.is_staff).filter(type=DestinationDetails.TOURS)
    tour_list = destination.tours.visible(request.user.is_staff).filter(display=True)

    assert_visible(request, destination)

    context = {
                  'destination': destination,
                  'details': detail_list,
                  'tours': tour_list
              } | global_context(request)

    return render(request, 'main/country_tours.html', context)


def region_tours(request, region_slug):
    region_obj = get_object_or_404(Region, slug=region_slug)
    countries = region_obj.destinations.visible(request.user.is_staff)
    tours = Tour.objects.visible(request.user.is_staff).filter(display=True)
    points = MapPoint.objects.all()

    assert_visible(request, region_obj)

    context = {
                  'region': region_obj,
                  'countries': countries,
                  'tours': tours,
                  'points': points
              } | global_context(request)
    return render(request, 'main/region-tours.html', context)


def country_tours_info(request, region_slug, country_slug, detail_slug):
    details = get_object_or_404(DestinationDetails,
                                destination__region__slug=region_slug,
                                destination__slug=country_slug,
                                slug=detail_slug, type=DestinationDetails.TOURS)

    assert_visible(request, details)

    context = {
                  'details': details
              } | global_context(request)

    return render(request, 'main/tour_info.html', context)
