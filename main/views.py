import enum
import emoji
import smtplib
from dataclasses import dataclass
from datetime import datetime
from functools import reduce, wraps
from os import path, pwrite
from typing import Dict, Iterator, List, Any
from urllib.parse import urlparse
from llama_cpp import CompletionChunk
from tabulate import tabulate
import openai

import ngram
from bs4 import BeautifulSoup
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.core.paginator import Paginator
from django.db.models import QuerySet, Func
from django.db.utils import OperationalError
from django.forms import modelform_factory, inlineformset_factory, modelformset_factory
from django.http import Http404, HttpResponseRedirect, HttpResponse, FileResponse, JsonResponse, HttpRequest, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from silk.profiling.profiler import silk_profile
from simple_history.models import HistoricalRecords
from django.urls import resolve, Resolver404

from vectordb import vectordb

from .forms import *
from .models import *
from .images import crop_to_dims, get_image_format
from .widgets import CountrySelectWidget


import torch
torch.set_num_threads(1)


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


def minify_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    return str(soup)


# Create your views here.
@silk_profile(name='Home Page')
def front_page(request):
    settings = Settings.load()

    rows = [FrontPageRow(settings.frontpage_tours_pos, 'tours'),
            FrontPageRow(settings.frontpage_map_pos, 'map'),
            FrontPageRow(settings.frontpage_blog_pos, 'articles',
                         Article.visible(request.user.is_staff).filter(type=Article.BLOG)[:3], 'Blogs',
                         reverse('blog')), FrontPageRow(settings.frontpage_news_pos, 'articles',
                                                        Article.visible(request.user.is_staff).filter(
                                                            type=Article.NEWS)[:3], 'News', reverse('news'))] + [
               FrontPageRow(pg.front_page_pos, 'section', pg, colour=pg.front_page_colour) for pg in
               Page.visible(request.user.is_staff).filter(front_page_pos__isnull=False).order_by('front_page_pos')]

    if (settings.testimonials_active or request.user.is_staff) and settings.testimonials_frontpage_pos:
        rows.append(FrontPageRow(settings.testimonials_frontpage_pos, 'testimonials'))

    highlight_rows: Dict[int, list] = {}
    for highlight in HightlightBox.visible(request.user.is_staff):
        if highlight.row in highlight_rows:
            highlight_rows[highlight.row].append(highlight)
        else:
            highlight_rows[highlight.row] = [highlight]

    for row_num, highlight_row in highlight_rows.items():
        highlight_row.sort(key=lambda box: box.col)
        rows.append(FrontPageRow(row_num, 'highlight', highlight_row))

    rows.sort(key=lambda row: row.pos if row.pos is not None else 1000)

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
        'points': MapPoint.objects.all().select_related('template'),
        'testimonials': Testimonial.visible(request.user.is_staff),
        'rows': rows,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            'SAIGA Tours Homepage',
            settings.logo_url,
            description='Come share some tours with us!',
        )
    }
    return render(request, 'main/front-page.html', context)


@dataclass
class FooterLink:
    name: str
    url: Optional[str] = None
    children: Optional[List['FooterLink']] = None


def global_context(request: HttpRequest) -> Dict[str, Any]:
    footer_links = [FooterLink(page.title, f'/{page.full_path}', [
        FooterLink(subpage.title, '/' + subpage.full_path)
        for subpage in page.children.visible(request.user.is_staff)
    ])
                    for page in Page.visible(request.user.is_staff).filter(parent=None, in_navbar=True).prefetch_related('children')]

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
        'tour_regions': Region.visible(request.user.is_staff).filter(display_tours=True),
        'guide_regions': Region.visible(request.user.is_staff).filter(display_guides=True),
        'pages': Page.visible(request.user.is_staff).filter(parent=None, in_navbar=True),
        'settings': Settings.load(),
        'footer_links': footer_links,
        'testing': request.COOKIES.get('testing', 'false') == 'true' and request.user.is_staff,
        'admin_subdomain': request.get_host().startswith('admin')
    }
    return context


class MetaInfoTypes(enum.Enum):
    ARTICLE = 'article'
    WEBSITE = 'website'


@dataclass
class MetaInfo:
    url: str
    title: str
    image_url: str
    description: str = ''
    type: MetaInfoTypes = MetaInfoTypes.WEBSITE


def destination_overview(request, region_slug, country_slug):
    destination = get_object_or_404(Destination, region__slug=region_slug, slug=country_slug)
    detail_list = destination.details.visible(request.user.is_staff).filter(type=DestinationDetails.GUIDE)
    tour_list = destination.tours.visible(request.user.is_staff).filter(display=True)

    assert_visible(request, destination)

    context = {
        'destination': destination,
        'details': detail_list,
        'tours': tour_list,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            destination.name,
            destination.card_img.url,
            f'Come look at the tours we offer in {destination.name}!',
        )
    }

    return render(request, 'main/destination.html', context)


def destination_details(request, region_slug, country_slug, detail_slug):
    return details_page(request, region_slug, country_slug, detail_slug, DestinationDetails.GUIDE)


def details_page(request, region_slug, country_slug, detail_slug, detail_type):
    details = get_object_or_404(DestinationDetails,
                                destination__region__slug=region_slug,
                                destination__slug=country_slug,
                                slug=detail_slug, type=detail_type)

    assert_visible(request, details)

    if request.user.is_staff:
        form_factory = modelform_factory(DestinationDetails, exclude=())
        form = form_factory(request.POST or None, request.FILES or None, instance=details)
        if request.method == 'POST' and form.is_valid():
            instance = form.save()
            if 'parent' in form.changed_data or 'slug' in form.changed_data:
                return redirect('page', instance.full_path)
    else:
        form = None

    context = {'details': details,
               'form': form,
               'meta': MetaInfo(
                   url=request.build_absolute_uri(),
                   title=details.title,
                   image_url=details.card_img.url,
                   description=details.excerpt or markdownify(details.content.strip())[:260]
               )}

    return render(request, 'main/destination_details.html', context)


# Just to get type hinting, not actually needed
def navbar(request):
    context = {
        'regions': Region.visible(request.user.is_staff),
        'pages': Page.visible(request.user.is_staff).filter(parent=None)
    }
    return render(request, 'main/navbar.html', context)


# @cache_for_users
def tour(request, slug):
    tour_obj = get_object_or_404(Tour, slug=slug)
    assert_visible(request, tour_obj)

    extensions = tour_obj.extensions.visible(request.user.is_staff)

    parent = None
    other_extensions = None
    if request.GET.get('parent') is not None:
        try:
            parent = Tour.objects.get(slug=request.GET.get('parent'))
            other_extensions = parent.extensions.visible(request.user.is_staff).exclude(pk=tour_obj.pk)
        except Tour.DoesNotExist:
            pass

    if request.user.is_staff:
        form_factory = modelform_factory(Tour, exclude=())
        form = form_factory(request.POST or None, request.FILES or None, instance=tour_obj)

        itinerary_formset_factory = inlineformset_factory(Tour, ItineraryDay, exclude=('tour',), extra=0)
        itinerary_formset = itinerary_formset_factory(request.POST or None, request.FILES or None, instance=tour_obj)

        stops_formset_factory = inlineformset_factory(Tour, Stop, exclude=('tour',), extra=0)
        stops_formset = stops_formset_factory(request.POST or None, instance=tour_obj)

        if request.method == 'POST' and form.is_valid() and itinerary_formset.is_valid() and stops_formset.is_valid():
            form.save()
            stops_formset.save()
            days: QuerySet[ItineraryDay] = itinerary_formset.save()

            for day in days:
                if day.template:
                    day.template.body = day.body
                    day.template.save()
                    for bound_day in day.template.itineraryday_set.all():
                        bound_day.body = day.body
                        bound_day.save()

            stops_formset = stops_formset_factory(None, instance=tour_obj)
            itinerary_formset = itinerary_formset_factory(None, request.FILES or None,
                                                          instance=tour_obj)
        elif request.method == 'POST':
            print(form.errors)

        all_tours = Tour.objects.all()
    else:
        form = None
        itinerary_formset = None
        stops_formset = None
        all_tours = None

    related_tours = None
    settings = Settings.load()
    if settings.related_tours_active == Settings.ActiveChoices.ACTIVE or settings.related_tours_active == Settings.ActiveChoices.STAFF_ONLY and request.user.is_staff:
        related_tours = map(lambda result: result.content_object, vectordb.filter(metadata__published=True, content_type__model='tour').search(tour_obj, k=3))

    context = {
        'tour': tour_obj,
        'all_tours': all_tours,
        'related_tours': related_tours,
        'form': form,
        'itinerary_forms': itinerary_formset,
        'stop_forms': stops_formset,
        'other_extensions': other_extensions,
        'parent': parent,
        'extensions': extensions,
        'position_templates': PositionTemplate.objects.all(),
        'itinerary_templates': ItineraryTemplate.objects.all(),
        'meta': MetaInfo(
            url=request.build_absolute_uri(),
            title=tour_obj.name,
            image_url=tour_obj.card_img.url,
            description=tour_obj.excerpt,
            type=MetaInfoTypes.ARTICLE
        )
    }
    return render(request, 'main/tour.html', context)


class Month(Func):
    function = 'EXTRACT'
    template = '%(function)s(MONTH from %(expressions)s)'
    output_field = models.IntegerField()


class Year(Func):
    function = 'EXTRACT'
    template = '%(function)s(YEAR from %(expressions)s)'
    output_field = models.IntegerField()


def tours(request):
    settings = Settings.load()
    annotated_tours = Tour.visible(request.user.is_staff).filter(Q(state__isnull=True)
                                                                 | Q(state__priority__isnull=True)
                                                                 | Q(state__priority__gte=0)
                                                                 ).filter(display=True
                                                                          ).annotate(m=Month('start_date'),
                                                                                     y=Year('start_date'))
    all_years = annotated_tours.values_list('y', flat=True)
    all_years = sorted(list(filter(None, list(dict.fromkeys(all_years)))))  # Removed duplicates and sorted
    grouped_tours = {}
    for year in all_years:
        grouped_tours[year] = {}
        all_months = annotated_tours.filter(y=year).values_list('m', flat=True)
        all_months = sorted(list(filter(None, list(dict.fromkeys(all_months)))))  # Removed duplicates and sorted
        for month in all_months:
            tours = annotated_tours.filter(y=year, m=month)
            grouped_tours[year][month] = tours

    pre_tours = Tour.visible(request.user.is_staff).filter(display=True).filter(Q(state__priority__gt=0) |
                                                                                Q(start_date__isnull=True))
    post_tours = Tour.visible(request.user.is_staff).filter(display=True).filter(state__priority__lt=0)
    context = {
        'pretours': pre_tours,
        'posttours': post_tours,
        'grouped_tours': grouped_tours,
        'destinations': Destination.visible(request.user.is_staff),
        'query': request.GET.get('q'),
        'meta': MetaInfo(
            url=request.build_absolute_uri(),
            title='Tours',
            image_url=settings.logo.url,
            description='Come see all the tours we have on offer!'
        )
    }
    return render(request, 'main/tours.html', context)


def tours_json(request):
    tours = Tour.visible(request.user.is_staff).filter(display=True)

    tour_url = "/media/animage.png"
    tour_url_without_media = tour_url.replace("/media/", "")

    data = [{
            'title': tour.name,
            'slug': tour.slug,
            'excerpt': tour.excerpt,
            'image': f"https://www.saigatours.com/resized-image{tour.card_img.url.replace('/media', '')}/500x350/",
            "state": {
                "label": tour.state.text,
                "border_colour": tour.state.border_color,
                "label_colour": tour.state.color,
            } if tour.state else None,
            'start_date': tour.start_date.strftime('%Y-%m-%d') if tour.start_date else None,
            'duration': tour.duration,
            'price': tour.price,
            'currency': tour.currency,
        } for tour in tours]
    return JsonResponse(data, safe=False)


def article(request, slug):
    article_obj = get_object_or_404(Article, slug=slug)
    assert_visible(request, article_obj)

    if request.user.is_staff:
        form_factory = modelform_factory(Article, exclude=())
        form = form_factory(request.POST or None, request.FILES or None, instance=article_obj)
        if request.method == 'POST' and form.is_valid():
            form.save()
    else:
        form = None

    context = {
        'article': article_obj,
        'form': form,
        'meta': MetaInfo(request.build_absolute_uri(),
                         article_obj.title,
                         article_obj.card_img.url,
                         article_obj.excerpt,
                         MetaInfoTypes.ARTICLE)
    }
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
        'checked_tags': checked_tags,
        'meta': MetaInfo(
            url=request.build_absolute_uri(),
            title='title',
            image_url=Settings.load().logo.url,
            description=f'See all the {title.lower()} we have on offer!'
        )
    }
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
        'tours': tours_list,
        'meta': MetaInfo(
            url=request.build_absolute_uri(),
            title=f'{region_obj.name} Guide',
            image_url=Settings.load().logo.url,
            description=f'Learn everything you need to know about {region_obj.name}'
        )
    }
    return render(request, 'main/region.html', context)


def page(request, path):
    try:
        page_obj = Page.reverse_path(path)
    except:
        raise Http404
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
        'form': form,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            page_obj.title,
            page_obj.card_img.url,
            page_obj.content[:36] + '...',
            MetaInfoTypes.ARTICLE
        )
    }
    return render(request, 'main/page.html', context)


@csrf_exempt
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        from_email = form.cleaned_data['from_email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        try:
            send_mail(f'Contact form submission: "{subject}"',
                      f'From: {from_email}\nSubject: {subject}\nMessage: \n{message}', 'contact-form@saigatours.com',
                      [Settings.load().contact_form_email])
            ContactSubmission.objects.create(from_email=from_email, subject=subject, message=message)
            messages.add_message(request, messages.SUCCESS, 'Successfully sent')
            return redirect('front-page')
        except BadHeaderError:
            form.add_error('from_email', 'Invalid header found.')
            ContactSubmission.objects.create(from_email=from_email, subject=subject, message=message, success=False)
            return render(request, 'main/contact.html', {'form': form})
        except smtplib.SMTPAuthenticationError:
            ContactSubmission.objects.create(from_email=from_email, subject=f'FAILED AUTH: {subject}', message=message, success=False)
            messages.add_message(request, messages.SUCCESS, 'Successfully sent')
            return render(request, 'main/contact.html', {'form': form})
        except OperationalError:
            ContactSubmission.objects.create(from_email=from_email, subject=f'FAILED EMOJI: {subject}', message=emoji.demojize(message), success=True)
            messages.add_message(request, messages.SUCCESS, 'Successfully sent')
            return render(request, 'main/contact.html', {'form': form})
    elif request.method == 'GET':
        form.fields['subject'].initial = request.GET.get('subject')
    context = {
        'form': form,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            'Contact Us',
            Settings.load().logo.url,
        )
    }
    return render(request, 'main/contact.html', context)


def destinations(request):
    if request.user.is_staff:
        DestinationFormsetFactory = modelformset_factory(Destination, fields=(
            'title_x', 'title_y', 'title_scale', 'title_rotation', 'title_curve'), extra=0)
        destination_formset = DestinationFormsetFactory(request.POST or None, prefix='countries')
        PointFormsetFactory = modelformset_factory(MapPoint, exclude=(), extra=0)
        point_formset = PointFormsetFactory(request.POST or None, prefix='points')
        form_context = {
            'country_forms': destination_formset,
            'point_forms': point_formset
        }
        if request.method == 'POST' and destination_formset.is_valid() and point_formset.is_valid():
            destination_formset.save()
            point_formset.save()
    else:
        form_context = {}

    context = {
                  'destinations': Destination.visible(request.user.is_staff),
                  'points': MapPoint.objects.all(),
                  'meta': MetaInfo(
                      request.build_absolute_uri(),
                      'Destinations',
                      Settings.load().logo.url,
                      "Come and see the destinations we have on offer!"
                  )
              } | form_context
    return render(request, 'main/destinations.html', context)


def favicon(request):
    return HttpResponseRedirect(Settings.load().logo_url)


def country_tours(request, region_slug, country_slug):
    destination = get_object_or_404(Destination, region__slug=region_slug, slug=country_slug)
    detail_list = destination.details.visible(request.user.is_staff).filter(type=DestinationDetails.TOURS)
    tour_list = destination.tours.visible(request.user.is_staff).filter(display=True)

    assert_visible(request, destination)

    context = {
        'destination': destination,
        'details': detail_list,
        'tours': tour_list,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            f'{destination.name} Group Tours',
            destination.card_img.url,
            destination.tour_meta or f'Learn more about the tours we offer to {destination.name}'
        )
    }

    return render(request, 'main/country_tours.html', context)


def region_tours(request, region_slug):
    region_obj = get_object_or_404(Region, slug=region_slug)
    countries = region_obj.destinations.visible(request.user.is_staff)
    tours = Tour.objects.visible(request.user.is_staff).filter(display=True, destinations__region=region_obj).distinct()
    points = MapPoint.objects.all()

    assert_visible(request, region_obj)

    context = {
        'region': region_obj,
        'title': region_obj.name if region_obj.name.lower().endswith("tours") else f'{region_obj.name} Tours',
        'countries': countries,
        'tours': tours,
        'points': points,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            f'Tours to {region_obj.name}',
            Settings.load().logo.url,
            f'Learn more about our tour offerings to {region_obj.name}'
        )
    }
    return render(request, 'main/region-tours.html', context)


def country_tours_info(request, region_slug, country_slug, detail_slug):
    return details_page(request, region_slug, country_slug, detail_slug, DestinationDetails.TOURS)


def crop_image(request, filename: str, width: int, height: int):
    removed_prefix = filename
    try:
        raw_image = Image.open(path.join(settings.MEDIA_ROOT, removed_prefix), mode='r')
    except FileNotFoundError:
        raise Http404
    image = autorotate(raw_image)

    cropped_image = crop_to_dims(image, width, height)

    img_format, save_func = get_image_format(request, image)

    response = HttpResponse(content_type=f'image/{img_format}')
    # cropped_image.save(response, img_format)
    save_func(cropped_image, response)
    return response


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


def modify_position_template(request, pk):
    if not request.user.is_staff or not request.method == 'POST':
        raise Http404

    position_template = get_object_or_404(PositionTemplate, pk=pk)

    if 'x' in request.POST.keys():
        position_template.x = request.POST.get('x')
    if 'y' in request.POST.keys():
        position_template.y = request.POST.get('y')
    if 'name' in request.POST.keys():
        position_template.name = request.POST.get('name')

    position_template.save()

    for stop in Stop.objects.filter(template=position_template):
        if 'x' in request.POST.keys():
            stop.x = position_template.x
        if 'y' in request.POST.keys():
            stop.y = position_template.y
        if 'name' in request.POST.keys() and stop.name is None:
            stop.name = position_template.name
        stop.save()

    return JsonResponse({'success': True})


def create_position_template(request):
    if not request.user.is_staff or not request.method == 'POST':
        raise Http404

    position_template = PositionTemplate.objects.create(x=request.POST.get('x'), y=request.POST.get('y'),
                                                        name=request.POST.get('name'))
    position_template.save()

    return JsonResponse({
        'pk': position_template.pk,
        'x': position_template.x,
        'y': position_template.y,
        'name': position_template.name
    })


def create_itinerary_template(request):
    if not request.user.is_staff or not request.method == 'POST':
        raise Http404

    template = ItineraryTemplate.objects.create(title=request.POST.get('title'),
                                                body=request.POST.get('body'))
    template.save()

    return JsonResponse({
        'pk': template.pk
    })


def error_404(request, exception):
    return render(request, '404.html', global_context(request) | {'no_canonical': True}, status=404)


def error_500(request):
    return render(request, '500.html', global_context(request) | {'no_canonical': True}, status=500)


def gen_500(request):
    if request.user.is_staff:
        hello = 5
        bye = hello / 0
        return HttpResponse('Well, darn. Apparently maths is broken.')
    else:
        return error_404(request, '')


def return_messages(request: HttpRequest) -> JsonResponse:
    # Getting the messages from the django message framework
    msgs = messages.get_messages(request)
    # Converting the messages to a list of dictionaries
    level_strings = {
        messages.DEBUG: 'secondary',
        messages.INFO: 'info',
        messages.SUCCESS: 'success',
        messages.WARNING: 'warning',
        messages.ERROR: 'danger'
    }
    msgs = [{'level': level_strings[msg.level], 'message': msg.message} for msg in msgs]
    # Returning the messages as a JsonResponse
    print("messages: ", msgs)
    response = JsonResponse({'messages': msgs})
    return response


def copy_map(request):
    if request.user.is_staff and request.method == 'POST':
        try:
            copy_from = Tour.objects.get(slug=request.POST.get('from'))
            copy_to = Tour.objects.get(slug=request.POST.get('to'))

            copy_to.stops.all().delete()
            for stop in copy_from.stops.all():
                stop.pk = None
                stop.tour = copy_to
                stop.save()

            copy_to.map_scale = copy_from.map_scale
            copy_to.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        raise Http404


def purge_cache(request):
    if request.user.is_staff or settings.DEBUG:
        try:
            invalidate_pages('all')
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        raise Http404


def testimonials(request):
    if not Settings.load().testimonials_active and not request.user.is_staff:
        raise Http404

    form_factory = modelform_factory(Testimonial,
                                     fields=('name', 'age', 'country', 'image', 'quote'),
                                     widgets={'country': CountrySelectWidget()})
    form = form_factory(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS, 'Testimonial submitted')
        return redirect('testimonials')

    context = {
        'testimonials': Testimonial.objects.filter(approved=True).order_by('?'),
        'form': form,
        'meta': MetaInfo(
            request.build_absolute_uri(),
            "Testimonials",
            Settings.load().logo.url,
            f'See what people have to say about {Settings.load().site_title}',
        )
    }
    return render(request, 'main/testimonials_page.html', context)


def links_list(request):
    if not request.user.is_staff:
        raise Http404

    return render(request, 'main/links.html')


def list_links(request):
    if not request.user.is_staff:
        raise Http404

    @dataclass
    class Link:
        model: models.Model
        field: models.Field
        url: str
        text: str

        def __str__(self):
            return f'{self.model.__name__}.{self.field.name} -> {self.url}'

        @property
        def empty(self):
            return self.url is None or self.url == ''

        @property
        def relative(self):
            return self.url.startswith('/') if not self.empty else False

        @property
        def model_link(self):
            return reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', args=(getattr(self.model, 'pk'),))

        @property
        def is_broken(self):
            print(f'Checking {self.url} - {self.resolves} - {self.relative}')
            # Check response code when pinging url
            if self.url is None:
                return True
            if self.resolves:
                return False
            if self.url.startswith('mailto:'):
                return False
            try:
                print(f'Checking {self.url}')
                response = requests.get(self.url)
                print(f'{self.url} -> {response.status_code}')
                return response.status_code != 200
            except Exception as e:
                print(f'Error checking {self.url}: {e}')
                return True

        @property
        def resolves(self):
            if self.empty:
                return False
            clean_url = self.url.split('#')[0].split('?')[0]
            if not clean_url.endswith('/'):
                clean_url += '/'
            try:
                resolve(clean_url)
                return True
            except Resolver404:
                try:
                    resolve(urlparse(clean_url).path)
                    return True
                except Resolver404:
                    return False

        @property
        def domain(self):
            if self.relative:
                return ''
            else:
                return f'{urlparse(self.url).scheme}://{urlparse(self.url).netloc}'

        @property
        def internal(self):
            return self.relative or self.domain == 'https://www.saigatours.com'


    def is_text_field(field):
        return isinstance(field, models.TextField)

    def is_history_model(model):
        return model.__name__.startswith('Historical')

    if not request.user.is_staff:
        raise Http404

    all_models = apps.get_app_config('main').get_models()
    links = []
    searched_fields = []

    for model in all_models:
        if not is_history_model(model):
            fields = model._meta.get_fields()
            for field in fields:
                if is_text_field(field):
                    searched_fields.append({
                        'model': model.__name__,
                        'field': field.name,
                    })
                    for instance in model.objects.all():
                        text = getattr(instance, field.name)
                        try:
                            if text is not None:
                                soup = BeautifulSoup(getattr(instance, field.name), 'html.parser')
                                for link in soup.find_all('a'):
                                    links.append(Link(instance, field, link.get('href'), link.text))
                        except Exception as e:
                            print(getattr(instance, field.name))
                            raise e

    # Print searched_fields as pretty table
    print(tabulate(searched_fields, headers='keys', tablefmt='fancy_grid'))

    return JsonResponse({'links': [{
        'model': str(link.model),
        'field': link.field.name,
        'url': link.url,
        'domain': link.domain,
        'text': link.text,
        'empty': link.empty,
        'relative': link.relative,
        'model_link': link.model_link,
        'resolves': link.resolves,
        'internal': link.internal,
        'is_broken': link.is_broken,
    } for link in links]})


def search(request):
    if not request.method == "GET":
        return JsonResponse({'error': 'Invalid request method'})

    query = request.GET.get('q', None)
    if query is None:
        return JsonResponse({'error': 'No query provided'})

    include_articles = request.GET.get('include_articles', False)
    include_pages = request.GET.get('include_pages', False)
    include_tours = request.GET.get('include_tours', False)
    include_destinationdetails = request.GET.get('include_destinationdetails', False)

    results = vectordb.filter(
        metadata__published=True,
        content_type__model__in=[
            'article' if include_articles else '',
            'page' if include_pages else '',
            'tour' if include_tours else '',
            'destinationdetails' if include_destinationdetails else '',
        ]
    ).search(query, k=20)

    print(results[0].id)
    print(results[0].metadata)
    print(results[0].content_object)
    print(results[0].content_type.model)
    print(results[0].__dict__)
    return JsonResponse({'results': [
        {
            'score': result.distance,
            'type': result.content_type.model,
            'metadata': result.metadata,
        } for result in results
    ]})


def generate_completion(text: str) -> str:
    result = openai.Completion.create(
       model="text-davinci-003",
       prompt=text,
       temperature=0.2,
       max_tokens=100,
    )

    completion = result.choices[0].text

#    from llama_cpp import Llama
#    llm = Llama(model_path="./wizard-vicuna-13B.ggmlv3.q2_K.bin")
#
#    result = llm(text, max_tokens=100)
#    print(result)
#
#    if isinstance(result, Iterator):
#        result = result.__next__()
#
#    completion = result.get("choices")[0].get("text")

    return completion


def ai_answer(request):
    if not request.method == "GET":
        return JsonResponse({'error': 'Invalid request method'})

    query = request.GET.get('q', None)
    if query is None:
        return JsonResponse({'error': 'No query provided'})

    context_results = vectordb.filter(metadata__published=True).search(query, k=20)

    completed = False
    initial_completion = None
    while not completed:
        try:
            context_titles = "\n-----\n".join([(f"ID: {result.id}\nType: {result.content_type.model}\nTitle: {result.metadata['title']}") for result in context_results])

            initial_promt = (f"You are an experienced tour guide with Saiga Tours, "          \
                             f"which takes tours into Central Asia and the Middle East.\n"  \
                             f"You are asked the following question by a customer:\n"       \
                             f"*Question:* '''{query}'''\n"                                 \
                             f"Which five of the following articles would be most relevant to your answer? " \
                             f"Answer with a comma separated list of IDs " \
                             f"ranked in order of relevance.\n\n" \
                             f"*Relevant articles:*\n{context_titles}" \
                             f"\n\n*Answer:*")

            initial_completion = generate_completion(initial_promt)
            completed = True
        except ValueError:
            context_results = context_results[:len(context_results) - 1]

    if initial_completion is None:
        return JsonResponse({'success': False})

    results = list(map(lambda res: int(res.strip()), initial_completion.split(',')))

    completed = False
    chat_completion = None
    while not completed:
        try:
            #context = "\n".join([f'{result.metadata["url"]}: {result.text[:500]}' for result in context_results if result.id in results])
            # use AiSummary
            context = "\n".join([f'{result.metadata["url"]}: {AiSummary.get_or_set_summary(result.content_object).summary}' for result in context_results if result.id in results])

            prompt = (f"*Reference Context:*\n{context}\n\n"                           \
                      f"*Scenario:*\n"                                                 \
                      f"You are an experienced tour guide with Saiga Tours, "          \
                      f"which takes tours into Central Asia and the Middle East.\n"    \
                      f"You are asked the following question by a customer:\n"         \
                      f"*Question:* '''{query}'''\n\n"                                 \
                      f"*Instructions:*\n"                                             \
                      f"Answer the question in the space below in an interesting "     \
                      f"and conversational tone. Link to at least one of the articles "\
                      f"above, with [markdown links](/link/location).\n"\
                      f"If there insufficient information to answer the question in the reference content, " \
                      f"link to the [contact page](/contact) and say nothing else. "           \
                      f"Avoid saying anything absent from the reference material.\n\n"      \
                      f"*Answer:*\n")

            print(prompt)
            #return JsonResponse({'answer': prompt})

            chat_completion = generate_completion(prompt)

            completed = True
        except ValueError:
            results = results[:len(results) - 1]

    if chat_completion is None:
        return JsonResponse({'success': False})

    print(chat_completion)
    return JsonResponse({'answer': chat_completion, 'success': True})

