from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from os import path
from typing import Optional, Dict, List, Any

import ngram
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import modelform_factory, inlineformset_factory
from django.http import Http404, HttpResponseRedirect, HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404, redirect

import analytics
from .forms import *
from .models import *


def assert_visible(request, model: DraftHistory):
    if not (model.published or request.user.is_staff):
        raise Http404


@dataclass
class FrontPageRow:
    pos: int
    type: str
    contents: Optional[Any] = None
    title: Optional[str] = None
    link: Optional[str] = None
    colour_before: Optional[str] = None
    colour: Optional[str] = None
    colour_after: Optional[str] = None


# Create your views here.
def front_page(request):
    settings = Settings.load()

    rows = [FrontPageRow(settings.frontpage_tours_pos, 'tours'), FrontPageRow(settings.frontpage_map_pos, 'map'),
            FrontPageRow(settings.frontpage_blog_pos, 'articles',
                         Article.visible(request.user.is_staff).filter(type=Article.BLOG)[:3], 'Blogs',
                         reverse('blog')), FrontPageRow(settings.frontpage_news_pos, 'articles',
                                                        Article.visible(request.user.is_staff).filter(
                                                            type=Article.NEWS)[:3], 'News', reverse('news'))] + [
               FrontPageRow(pg.front_page_pos, 'section', pg, colour=pg.front_page_colour) for pg in
               Page.visible(request.user.is_staff).filter(front_page_pos__isnull=False).order_by('front_page_pos')]

    highlight_rows: Dict[int, list] = {}
    for highlight in HightlightBox.visible(request.user.is_staff):
        if highlight.row in highlight_rows:
            highlight_rows[highlight.row].append(highlight)
        else:
            highlight_rows[highlight.row] = [highlight]

    for row_num, highlight_row in highlight_rows.items():
        highlight_row.sort(key=lambda box: box.col)
        rows.append(FrontPageRow(row_num, 'highlight', highlight_row))

    rows.sort(key=lambda row: row.pos)

    for i, row in enumerate(rows[1:]):
        if row.type == 'section' and rows[i].type == 'section':
            row.colour_before = rows[i].colour
            rows[i].colour_after = row.colour

    context = {
                  'tours': Tour.visible(request.user.is_staff).filter(display=True),
                  'banners': BannerPhoto.objects.filter(active=True).order_by('?'),
                  'frontpage_sections': Page.visible(request.user.is_staff).filter(
                      front_page_pos__isnull=False).order_by('front_page_pos'),
                  'highlights': HightlightBox.visible(request.user.is_staff),
                  'destinations': Destination.visible(request.user.is_staff),
                  'points': MapPoint.objects.all(),
                  'rows': rows
              } | global_context(request)
    return render(request, 'main/front-page.html', context)


@dataclass
class FooterLink:
    name: str
    url: Optional[str] = None
    children: Optional[List['FooterLink']] = None


def global_context(request):
    footer_links = [FooterLink(page.title, reverse('page', args=[page.slug]), [
        FooterLink(subpage.title, reverse('page', args=[subpage.slug]))
        for subpage in page.children.visible(request.user.is_staff)
    ])
                    for page in Page.visible(request.user.is_staff).filter(parent=None)]

    footer_links += [FooterLink('tours', reverse('tours'), [
        FooterLink(region.name, reverse('tours', args=[region.slug]), [
            # FooterLink(country.name)
            # for country in region.destinations.visible(request.user.is_staff)
        ])
        for region in Region.visible(request.user.is_staff)
    ]),
                     FooterLink('destination guides', reverse('destinations'), [
                         FooterLink(region.name, reverse('tours', args=[region.slug]), [
                             # FooterLink(country.name)
                             # for country in region.destinations.visible(request.user.is_staff)
                         ])
                         for region in Region.visible(request.user.is_staff)
                     ]),
                     FooterLink('other', None, [
                         FooterLink('Blog', reverse('blog')),
                         FooterLink('News', reverse('news')),
                         FooterLink('Contact', reverse('contact'))
                     ])
                     ]

    context = {
                  'regions': Region.visible(request.user.is_staff),
                  'pages': Page.visible(request.user.is_staff).filter(parent=None, in_navbar=True),
                  'settings': Settings.load(),
                  'footer_links': footer_links,
              } | analytics.analytics_context(request)
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
            stops_formset = stops_formset_factory(None, instance=tour_obj)
            itinerary_formset = itinerary_formset_factory(None, request.FILES or None,
                                                          instance=tour_obj)
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
                  'destinations': Destination.visible(request.user.is_staff),
                  'query': request.GET.get('q')
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


def destinations(request):
    context = {'destinations': Destination.visible(request.user.is_staff),
               'points': MapPoint.objects.all()
               } | global_context(request)
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


def resized_imaged(request, filename: str, width: int = None, height: int = None):
    image = Image.open(path.join(settings.MEDIA_ROOT, filename), mode='r')
    if width is not None or height is not None:
        (old_width, old_height) = image.size

        ar = old_width / old_height
        if old_width / width > old_width / height:
            height = int(width / ar)
        else:
            width = int(height * ar)

        if height < old_height:
            image = image.resize((width, height))

        response = HttpResponse(content_type='image/webp')
        # noinspection PyTypeChecker
        image.save(response, 'webp')
        return response


def crop_to_ar(image: Image, ratio: float) -> Tuple[int, int, int, int]:
    (width, height) = image.size
    if abs(width - ratio * height) < 5:
        return image
    elif width > ratio * height:
        new_height = height
        new_width = height * ratio
    else:
        new_width = width
        new_height = width / ratio

    return (
        (width - new_width) // 2, (height - new_height) // 2, (width + new_width) // 2, (height + new_height) // 2)


def create_map(request, slug: str):
    if request.user.is_staff:
        tour_obj = get_object_or_404(Tour, slug=slug)
        if tour_obj.stops.count() == 0:
            tour_obj.stops.create(name='Initial stop')
            messages.add_message(request, messages.SUCCESS, 'Created initial point')
        else:
            messages.add_message(request, messages.INFO, 'Map already exists')
        return redirect('tour', slug)
    else:
        raise Http404


def view_document(request, slug: str):
    file = get_object_or_404(FileUpload, slug=slug)
    return FileResponse(file.file)
