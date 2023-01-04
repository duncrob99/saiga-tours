import enum
import smtplib
from dataclasses import dataclass
from datetime import datetime
from functools import reduce, wraps
from os import path
from typing import Dict, List, Any

import ngram
from bs4 import BeautifulSoup
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.core.paginator import Paginator
from django.db.models import QuerySet, Func
from django.forms import modelform_factory, inlineformset_factory, modelformset_factory
from django.http import Http404, HttpResponseRedirect, HttpResponse, FileResponse, JsonResponse, HttpRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from silk.profiling.profiler import silk_profile

from .forms import *
from .models import *
from .images import crop_to_dims, get_image_format
from .widgets import CountrySelectWidget


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

    rows = [FrontPageRow(settings.frontpage_tours_pos, 'tours'), FrontPageRow(settings.frontpage_map_pos, 'map'),
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
            request.get_raw_uri(),
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


def global_context(request):
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
            request.get_raw_uri(),
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
                   url=request.get_raw_uri(),
                   title=details.title,
                   image_url=details.card_img.url,
                   description=details.content[:40]
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

    context = {
        'tour': tour_obj,
        'all_tours': all_tours,
        'form': form,
        'itinerary_forms': itinerary_formset,
        'stop_forms': stops_formset,
        'other_extensions': other_extensions,
        'parent': parent,
        'extensions': extensions,
        'position_templates': PositionTemplate.objects.all(),
        'itinerary_templates': ItineraryTemplate.objects.all(),
        'meta': MetaInfo(
            url=request.get_raw_uri(),
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
            url=request.get_raw_uri(),
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
        'meta': MetaInfo(request.get_raw_uri(),
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
            url=request.get_raw_uri(),
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
            url=request.get_raw_uri(),
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
            request.get_raw_uri(),
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
                      f'From: {from_email}\nSubject: {subject}\nMessage: \n{message}', from_email,
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
    elif request.method == 'GET':
        form.fields['subject'].initial = request.GET.get('subject')
    context = {
        'form': form,
        'meta': MetaInfo(
            request.get_raw_uri(),
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
                      request.get_raw_uri(),
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
            request.get_raw_uri(),
            f'Tours to {destination.name}',
            destination.card_img.url,
            f'Learn more about the tours we offer to {destination.name}'
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
        'countries': countries,
        'tours': tours,
        'points': points,
        'meta': MetaInfo(
            request.get_raw_uri(),
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
        return Http404

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
        return Http404

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
        return Http404

    template = ItineraryTemplate.objects.create(title=request.POST.get('title'),
                                                body=request.POST.get('body'))
    template.save()

    return JsonResponse({
        'pk': template.pk
    })


def error_404(request, exception):
    return render(request, '404.html', global_context(request), status=404)


def error_500(request):
    return render(request, '500.html', global_context(request), status=500)


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
        return Http404


def purge_cache(request):
    if request.user.is_staff or settings.DEBUG:
        try:
            invalidate_pages('all')
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return Http404


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
            request.get_raw_uri(),
            "Testimonials",
            Settings.load().logo.url,
            f'See what people have to say about {Settings.load().site_title}',
        )
    }
    return render(request, 'main/testimonials_page.html', context)
