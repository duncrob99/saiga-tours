import json
from datetime import timedelta
from io import BytesIO
from typing import Tuple, Optional
from markdownify import markdownify

import requests
from bs4 import BeautifulSoup as bs
import inspect
from PIL import Image
from ckeditor_uploader.fields import RichTextUploadingField
from colorfield.fields import ColorField
from django_countries.fields import CountryField

from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models import F, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import classproperty
from simple_history.models import HistoricalRecords
from django.contrib.sitemaps import ping_google
from django.conf import settings
from django.db.models.functions import Coalesce

from .images import crop_to_ar, autorotate

import openai
import hashlib

def clean_html(html: str):
    soup = bs(html, 'html.parser')
    img_tags = soup.find_all('img')

    for img in img_tags:
        if img.get('src').startswith('/resized-image/'):
            img['src'] = img['src'].replace('/resized-image/', '/media/')
            img['src'] = '/'.join(img['src'].split('/')[:-2])

        if img.get('data-cke-saved-src') and img.get('data-cke-saved-src').startswith('/resized-image/'):
            img['data-cke-saved-src'] = img['data-cke-saved-src'].replace('/resized-image/', '/media/')
            img['data-cke-saved-src'] = '/'.join(img['data-cke-saved-src'].split('/')[:-2])

    print('soupstr: ', soup.str())
    return soup.prettify().replace(
        '<span style="background-color:rgba(220,220,220,0.5)"><img src="data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==" style="height:15px; width:15px" title="Click and drag to move"></span>',
        '')


def is_html_clean(html: str):
    soup = bs(html, 'html.parser')
    img_tags = soup.find_all('img')
    img_srcs = [img.get('src') for img in img_tags]

    not_resized = [not img.startswith('/resized-image/') for img in img_srcs]

    print('soupstr: ', soup.str())
    has_drag_img = soup.prettify().find(
        '<span style="background-color:rgba(220,220,220,0.5)"><img src="data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==" style="height:15px; width:15px" title="Click and drag to move"></span>') != -1

    if all(not_resized) and not has_drag_img:
        return True
    else:
        return False


def RichTextWithPlugins(*args, **kwargs):
    def plugin_path(name: str) -> str:
        return static(f'js/ckeditor/plugins/{name}/')

    def plugin_def(name: str) -> Tuple[str, str, str]:
        return name, plugin_path(name), 'plugin.js'

    field = RichTextUploadingField(external_plugin_resources=[
        plugin_def('splitsection'),
        plugin_def('imagefan')
    ], extra_plugins=['splitsection', 'imagefan'], *args, **kwargs)

    stack = inspect.stack()[1]
    model_name = inspect.getmodule(stack[0]).__name__.split('.')[0] + '.' + stack.function

    # @receiver(post_save, sender=model_name)
    def clean_field_input(sender, instance: models.Model, **kwargs):
        print('cleaning')
        field_name = field.name
        content = getattr(instance, field_name)
        print('content: ', content)
        if not is_html_clean(content):
            setattr(instance, field_name, clean_html(content))
            instance.save()

    return field


class DraftHistoryManager(models.Manager):
    def all_published(self):
        return self.filter(
            Q(published_bool=True) | Q(published_date__lte=timezone.now()))

    def visible(self, su: bool):
        return self.all() if su else self.all_published()


class DraftHistory(models.Model):
    history = HistoricalRecords(inherit=True, excluded_fields=['published'])
    published_bool = models.BooleanField(default=False)
    published_date = models.DateTimeField(null=True, blank=True)
    objects = DraftHistoryManager()

    published_q = Q(published_bool=True) & Q(published_date__isnull=True) | Q(published_date__lte=timezone.now())

    class Meta:
        abstract = True

    @property
    def published(self):
        if self.published_date is not None:
            return self.published_date < timezone.now()
        else:
            return self.published_bool

    @classproperty
    def all_published(cls):
        return cls.objects.filter(
            Q(published_bool=True) | Q(published_date__lte=timezone.now()))

    @classmethod
    def visible(cls, su: bool):
        return cls.objects.all() if su else cls.all_published


class Region(DraftHistory):
    name = models.CharField(max_length=400)
    slug = models.SlugField(primary_key=True)
    tour_blurb = RichTextWithPlugins(config_name='default', null=True, blank=True)

    banner_img = models.ImageField(null=True, blank=True)
    banner_x = models.FloatField(default=50)
    banner_y = models.FloatField(default=50)

    list_order = models.IntegerField(default=0)
    display_tours = models.BooleanField(default=True)
    display_guides = models.BooleanField(default=True)

    def get_caches_to_invalidate(self, previous):
        return 'all'

    def save(self, *args, **kwargs):
        super(Region, self).save(*args, **kwargs)
        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['list_order', 'name']


class Destination(DraftHistory):
    name = models.CharField(max_length=400)
    card_img = models.ImageField()
    slug = models.SlugField()
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, related_name='destinations')
    description = RichTextWithPlugins(config_name='default', null=True, blank=True)
    tour_blurb = RichTextWithPlugins(config_name='default', null=True, blank=True)
    map_colour = ColorField(null=True, blank=True)

    title_x = models.FloatField(null=True, blank=True)
    title_y = models.FloatField(null=True, blank=True)
    title_scale = models.FloatField(null=True, blank=True)
    title_rotation = models.FloatField(null=True, blank=True)
    title_curve = models.FloatField(null=True, blank=True)

    tour_banner = models.ImageField(null=True, blank=True)
    tour_banner_x = models.FloatField(default=50)
    tour_banner_y = models.FloatField(default=50)
    guide_banner = models.ImageField(null=True, blank=True)
    guide_banner_x = models.FloatField(default=50)
    guide_banner_y = models.FloatField(default=50)

    def get_caches_to_invalidate(self, previous):
        return 'all'

    def __str__(self):
        return self.name

    @property
    def guide_details(self):
        return self.details.filter(type=DestinationDetails.GUIDE)

    @property
    def tour_info(self):
        return self.details.filter(type=DestinationDetails.TOURS)

    class Meta:
        ordering = ['region', 'name']
        unique_together = [['region', 'slug'], ['region', 'name']]


class AiSummary(models.Model):
    model = models.CharField(max_length=100)
    instance = models.CharField(max_length=100)
    summary = models.TextField()
    full_text_hash = models.CharField(max_length=100)

    def __str__(self):
        return f"Summary of {self.instance} ({self.model})"

    @classmethod
    def get_summary(cls, instance) -> 'AiSummary' or None:
        try:
            return cls.objects.get(instance=instance.__str__(), model=instance.__class__.__name__)
        except cls.DoesNotExist:
            return None

    @classmethod
    def set_summary(cls, instance, full_text = None):
        summary = cls.get_summary(instance)
        if summary is None:
            summary = cls.objects.create(instance=instance.__str__(), model=instance.__class__.__name__)
        full_text = full_text or instance.get_vectordb_text()
        summary.full_text_hash = hashlib.sha256(full_text.encode('utf-8')).hexdigest()
        summary.summary = cls.generate_summary(full_text)
        summary.save()

    @classmethod
    def get_or_set_summary(cls, instance) -> 'AiSummary':
        summary = cls.get_summary(instance)
        full_text = instance.get_vectordb_text()
        if summary is None or summary.full_text_hash != hashlib.sha256(full_text.encode('utf-8')).hexdigest():
            cls.set_summary(instance, full_text)

        summary = cls.get_summary(instance)
        if summary is None:
            raise Exception("Summary could not be generated")

        return summary

    @classmethod
    def generate_summary(cls, source: str or models.Model):
        if isinstance(source, str):
            full_text = source
        else:
            full_text = source.get_vectordb_text()
        prompt = (f"Summarise this text such that it still contains all the "  \
                  f"information that could be used to "                        \
                  f"answer questions about the text.\n\n"                      \
                  f"{full_text}\n\n" \
                  f"Summary:")[:2048]

        completion = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0,
            max_tokens=512
        )

        print(completion)
        return completion.choices[0].text


class DestinationDetails(DraftHistory):
    TOURS = 't'
    GUIDE = 'g'
    TYPE_CHOICES = (
        (TOURS, 'Tours'),
        (GUIDE, 'Guide')
    )

    title = models.CharField(max_length=100)
    slug = models.SlugField()
    content = RichTextWithPlugins(config_name='default')
    order = models.IntegerField()
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='details')
    type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    card_img = models.ImageField()
    linked_tours = models.ManyToManyField('Tour', blank=True)

    banner_img = models.ImageField(null=True, blank=True)
    banner_x = models.FloatField(default=50)
    banner_y = models.FloatField(default=50)

    def get_vectordb_text(self):
        return f"Title: {self.title} for {self.destination}\n" \
            f"{markdownify(self.content)}"

    def get_vectordb_metadata(self):
        return {
            'title': self.title,
            'destination': self.destination.name,
            'region': self.destination.region.name,
            'type': self.type,
            'url': self.get_absolute_url(),
            'image': self.card_img.url,
            'published': self.published,
        }

    def get_caches_to_invalidate(self, previous):
        return 'all'

    def save(self, *args, **kwargs):
        super(DestinationDetails, self).save(*args, **kwargs)
        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    class Meta:
        verbose_name_plural = 'Destination details'
        unique_together = [['destination', 'order', 'type'],
                           ['destination', 'title', 'type'],
                           ['destination', 'slug', 'type']]
        ordering = ['destination', 'order', 'slug']

    def __str__(self):
        return f'{self.title} for {self.destination.name}'

    def get_absolute_url(self):
        view = 'tours' if self.type == self.TOURS else 'destination-details'
        return reverse(view, args=[self.destination.region.slug, self.destination.slug, self.slug])


class State(models.Model):
    text = models.CharField(max_length=50, null=True, blank=True)
    color = ColorField(default=None, null=True, blank=True)
    text_color = ColorField(default=None, null=True, blank=True)
    border_color = ColorField(default=None, null=True, blank=True)
    priority = models.IntegerField(null=True, blank=True, help_text='0=same as no priority, 1 further to top, '
                                                                    '-1 below no priority, etc. Equal '
                                                                    'priorities will be sorted as per usual.')
    history = HistoricalRecords()

    def get_caches_to_invalidate(self, previous):
        changed_destinations = Destination.objects.filter(tours__state=self)
        changed_regions = Region.objects.filter(destinations__in=changed_destinations)
        changed_details = DestinationDetails.objects.filter(linked_tours__state=self)
        destination_paths = [reverse('tours', args=[d.region.slug, d.slug]) for d in changed_destinations]
        region_paths = [reverse('tours', args=[region.slug]) for region in changed_regions]
        detail_paths = [reverse('tours', args=[d.destination.region.slug, d.destination.slug, d.slug]) for d in changed_details]
        tours_path = reverse('tours')
        return destination_paths + region_paths + detail_paths + [tours_path]

    def __str__(self):
        return self.text

    class Meta:
        ordering = [F('priority').desc(), 'text']


class Tour(DraftHistory):
    name = models.CharField(max_length=400)
    slug = models.SlugField(unique=True)
    destinations = models.ManyToManyField(Destination, related_name='tours')
    start_date = models.DateField(null=True, blank=True)
    duration = models.IntegerField(null=True)
    description = RichTextWithPlugins()
    excerpt = models.TextField()
    itinerary_doc = models.ForeignKey('FileUpload', on_delete=models.SET_NULL, null=True, blank=True)

    card_img = models.ImageField()
    banner_img = models.ImageField(null=True, blank=True)
    banner_x = models.FloatField(null=True, blank=True)
    banner_y = models.FloatField(null=True, blank=True)

    price = models.DecimalField(max_digits=8, decimal_places=2)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    extensions = models.ManyToManyField('self', blank=True, symmetrical=False)
    display = models.BooleanField(default=True)
    keywords = models.TextField(null=True, blank=True)

    map_scale = models.FloatField(default=1)

    start_location = models.CharField(max_length=100, null=True, blank=True)
    end_location = models.CharField(max_length=100, null=True, blank=True)

    last_modified = models.DateTimeField(auto_now=True, null=True)

    def get_caches_to_invalidate(self, previous):
        changed_destinations = Destination.objects.filter(tours=self)
        changed_regions = Region.objects.filter(destinations__in=changed_destinations)
        changed_details = DestinationDetails.objects.filter(linked_tours=self)
        destination_paths = [reverse('tours', args=[d.region.slug, d.slug]) for d in changed_destinations]
        region_paths = [reverse('tours', args=[region.slug]) for region in changed_regions]
        detail_paths = [reverse('tours', args=[d.destination.region.slug, d.destination.slug, d.slug]) for d in changed_details]
        tours_path = reverse('tours')
        return destination_paths + region_paths + detail_paths + [tours_path, self.get_absolute_url()]

    def get_vectordb_text(self):
        return f"Title: {self.name}\n" \
            f"Description: {self.excerpt}\n" \
            f"Duration: {self.duration} days\n" \
            f"Price: ${self.price}\n" \
            f"Start date: {self.start_date.strftime('%d/%m/%Y') if self.start_date is not None else 'None'}\n" \
            f"Start location: {self.start_location}\n" \
            f"End location: {self.end_location}\n" \
            f"Keywords: {self.keywords}\n" \
            f"Destinations: {', '.join([d.name for d in self.destinations.all()])}\n" \
            f"State: {self.state.text if self.state is not None else 'None'}\n" \
            f"Description: {markdownify(self.description)}" \

    def get_vectordb_metadata(self):
        return {
            'title': self.name,
            'description': self.excerpt,
            'duration': self.duration,
            'price': float(self.price),
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date is not None else None,
            'start_location': self.start_location,
            'end_location': self.end_location,
            'keywords': self.keywords,
            'destinations': [d.name for d in self.destinations.all()],
            'state': self.state.text if self.state is not None else None,
            'url': self.get_absolute_url(),
            'image': self.card_img.url,
            'published': self.published,
        }

    @property
    def dated(self):
        return self.start_date is not None

    @property
    def end_date(self):
        return self.start_date + timedelta(days=(self.duration or 1) - 1) if self.start_date is not None else None

    @property
    def close_tours(self):
        return sorted(Tour.objects.exclude(slug=self.slug).filter(display=True, start_date__isnull=False),
                      key=lambda tour: abs(tour.start_date - self.start_date))[:4]

    @property
    def close_published_tours(self):
        ordered_tours = sorted(Tour.objects.exclude(slug=self.slug).filter(display=True, start_date__isnull=False),
                               key=lambda tour: abs(tour.start_date - self.start_date))
        return list(filter(lambda tour: tour.published, ordered_tours))[:4]

    def __str__(self):
        return self.name

    @property
    def priority(self):
        if self.state is not None:
            return self.state.priority
        else:
            return 9999 ** 9999

    def get_absolute_url(self):
        return reverse('tour', args=[self.slug])

    def save(self, *args, **kwargs):
        super(Tour, self).save(*args, **kwargs)
        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    class Meta:
        ordering = [Coalesce('state__priority', 0).desc(), 'start_date', 'price']


class ItineraryTemplate(models.Model):
    title = models.CharField(max_length=100)
    body = RichTextWithPlugins()
    history = HistoricalRecords()

    def get_caches_to_invalidate(self, previous):
        instances = self.itineraryday_set.all()
        return [reverse('tour', args=[instance.tour.slug]) for instance in instances]

    def __str__(self):
        return self.title


class ItineraryDay(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerary')
    title = models.CharField(max_length=100, null=True, blank=True)
    day = models.IntegerField()
    body = RichTextWithPlugins(null=True, blank=True)
    history = HistoricalRecords()
    template = models.ForeignKey(ItineraryTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    def get_caches_to_invalidate(self, previous):
        return [reverse('tour', args=[self.tour.slug])]

    class Meta:
        unique_together = [['tour', 'day']]
        ordering = [F('tour'), 'day']
        # constraints = [models.CheckConstraint(
        #     check=Q(title__isnull=False, body__isnull=False) | Q(template__isnull=False),
        #     name='template_or_content'
        # )]

    @property
    def date(self):
        if self.tour.start_date is not None:
            return self.tour.start_date + timedelta(days=self.day - 1)

    def __str__(self):
        return f'{self.tour} day {self.day}'


def check_slug(name: str):
    new_slug = name.lower().replace(' ', '_')
    if len(Tag.objects.filter(slug=new_slug)) > 0:
        raise ValidationError(f'Name results in non-unique slug, {new_slug}')


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, validators=[check_slug])
    slug = models.SlugField(max_length=100, editable=False, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = self.name.lower().replace(' ', '_')
        super(Tag, self).save(*args, **kwargs)


class Author(DraftHistory):
    name = models.CharField(max_length=100)
    picture = models.ImageField()
    blurb = RichTextWithPlugins(config_name='default')

    def get_caches_to_invalidate(self, previous):
        articles = self.article_set.all()
        return [reverse('article', args=[article.slug]) for article in articles]

    def __str__(self):
        return self.name


class Article(DraftHistory):
    NEWS = 'n'
    BLOG = 'b'
    TYPE_CHOICES = [
        (NEWS, 'News'),
        (BLOG, 'Blog')
    ]

    slug = models.SlugField(primary_key=True)
    title = models.CharField(max_length=400)
    creation = models.DateTimeField(auto_now_add=True)
    content = RichTextWithPlugins(config_name='default')
    excerpt = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=NEWS)
    card_img = models.ImageField(null=True)
    keywords = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    banner_img = models.ImageField(null=True, blank=True)
    banner_x = models.FloatField(null=True, blank=True)
    banner_y = models.FloatField(null=True, blank=True)

    def get_caches_to_invalidate(self, previous):
        return [self.get_absolute_url(), reverse('news') if self.type == self.NEWS else reverse('blog')]

    @property
    def date(self):
        if self.published_date is not None:
            return self.published_date
        else:
            return self.creation

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super(Article, self).save(*args, **kwargs)
        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    class Meta:
        ordering = [Coalesce('state__priority', 0).desc(), '-order', '-creation', 'title']

    def tag_list(self) -> str:
        return ' '.join([str(tag) for tag in self.tags.all()])

    def get_absolute_url(self):
        return reverse('article', args=[self.slug])

    def get_vectordb_text(self):
        return f'Title: {self.title}\nTags:{self.tag_list()}\nDescription:{self.excerpt}\n{markdownify(self.content)}'

    def get_vectordb_metadata(self):
        date = self.date
        return {
            'title': self.title,
            'author': self.author.name if self.author else None,
            'description': self.excerpt,
            'tags': self.tag_list(),
            'url': self.get_absolute_url(),
            'image': self.card_img.url if self.card_img else None,
            'date': date.strftime('%Y-%m-%d') if date else None,
            'state': self.state.text if self.state else None,
            'type': self.type,
            'published': self.published,
        }


class Page(DraftHistory):
    slug = models.SlugField()
    title = models.CharField(max_length=400)
    subtitle = models.CharField(max_length=200, default='')
    content = RichTextWithPlugins(config_name='default')
    card_img = models.ImageField()
    banner_img = models.ImageField(null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    sibling_label = models.CharField(max_length=100, default='Extra')
    in_navbar = models.BooleanField(default=True)
    front_page_pos = models.IntegerField(null=True, blank=True)
    front_page_colour = ColorField(default='#FFFFFF')
    banner_pos_x = models.FloatField(null=True, blank=True)
    banner_pos_y = models.FloatField(null=True, blank=True)

    last_mod = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = [['parent', 'slug']]
        ordering = ['title', 'slug']

    @property
    def breadcrumb(self):
        if self.parent:
            return self.parent.breadcrumb + ' > ' + self.title
        else:
            return self.title

    def get_vectordb_text(self):
        return f'Title: {self.title}\nBreadcrumb: {self.breadcrumb}\n{markdownify(self.content)}'

    def get_vectordb_metadata(self):
        return {
            'title': self.title,
            'description': self.subtitle,
            'breadcrumb': self.breadcrumb,
            'url': self.get_absolute_url(),
            'image': self.card_img.url,
            'published': self.published,
        }

    @property
    def card_img_url(self):
        # Return card_img.url without the media url
        return self.card_img.url[len(settings.MEDIA_URL):]

    def get_caches_to_invalidate(self, previous):
        if self.in_navbar:
            return "all"
        elif self.front_page_pos is not None:
            return [reverse('front-page'), self.get_absolute_url()]
        else:
            return [self.get_absolute_url()]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super(Page, self).save(*args, **kwargs)
        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    @property
    def full_path(self):
        if self.parent is None:
            return self.slug
        else:
            return self.parent.full_path + '/' + self.slug

    @classmethod
    def reverse_path(cls, path: str):
        split_path = path.split('/')
        page = cls.objects.get(slug=split_path[0], parent=None)
        for slug in split_path[1:]:
            if slug != '':
                page = cls.objects.get(slug=slug, parent=page)
        return page

    @property
    def published_children(self):
        return self.children.all_published

    @property
    def siblings(self):
        if self.parent is not None:
            return self.parent.children.exclude(pk=self.pk)
        else:
            return Page.objects.none()

    @property
    def published_siblings(self):
        return self.siblings.filter(DraftHistory.published_q)

    @property
    def level(self):
        if self.parent is None:
            return 0
        else:
            return self.parent.level + 1


    @property
    def has_children(self):
        return not (self.children.count() == 0 and self.testimonial_children.count() == 0)

    @property
    def has_published_children(self):
        return not (self.published_children().count() == 0 and (self.testimonial_children.count() == 0 or not Settings.load().testimonials_active))


    def get_absolute_url(self):
        return '/' + self.full_path


@receiver(post_save)
def validate_image_size(sender, instance, created, **kwargs):
    if hasattr(instance, 'card_img') and instance.card_img:
        with Image.open(instance.card_img) as image:
            format = image.format
            image = autorotate(image)
            ratio = 3 / 2
            (width, height) = image.size
            if abs(width - ratio * height) <= 5:  # Prevents infinte loop when saving
                return
            new_image = crop_to_ar(image, ratio)

        img_io = BytesIO()
        new_image.save(img_io, format=format)
        instance.card_img.save(instance.card_img.name, File(img_io))


class Settings(models.Model):
    title = models.CharField(max_length=30)
    active = models.BooleanField(default=False)
    accent_background = ColorField(default='#87cefa')
    accent_foreground = ColorField(default='#000000')
    accent_hover_background = ColorField(default='#87cefa')
    accent_hover_foreground = ColorField(default='#000000')
    site_title = models.CharField(max_length=500, default='Crowley Tours')
    catchphrase = models.CharField(max_length=500, default='We do cool tours')
    logo = models.FileField(null=True, blank=True)

    twitter_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)
    facebook_link = models.URLField(blank=True, null=True)
    tiktok_link = models.URLField(blank=True, null=True)

    price_prefix = models.CharField(max_length=10, default='US$')
    rounded_card_headers = models.BooleanField(default=True)
    corner_radius = models.FloatField(default=20)
    contact_form_email = models.EmailField(default='duncrob99@gmail.com')
    banner_delay = models.FloatField(default=15)
    banner_initial_delay = models.FloatField(default=15)
    banner_transition_time = models.FloatField(default=2)
    pagination_middle_size = models.PositiveSmallIntegerField(default=2)
    pagination_outer_size = models.PositiveSmallIntegerField(default=2)
    articles_per_page = models.PositiveIntegerField(default=10)

    frontpage_map_pos = models.PositiveSmallIntegerField(default=1)
    frontpage_highlights_pos = models.PositiveSmallIntegerField(default=2)
    frontpage_tours_pos = models.PositiveSmallIntegerField(default=3)
    frontpage_blog_pos = models.PositiveSmallIntegerField(default=4)
    frontpage_news_pos = models.PositiveSmallIntegerField(default=5)

    # Footer info
    contact_number = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    footer_email = models.CharField(max_length=200, null=True, blank=True)
    copyright = models.CharField(max_length=200, null=True, blank=True)

    testimonials_active = models.BooleanField(default=False)
    testimonials_parent = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True, related_name='testimonial_children')
    testimonials_navbar_pos = models.PositiveSmallIntegerField(default=1)
    testimonials_frontpage_pos = models.PositiveSmallIntegerField(default=6, null=True, blank=True)

    class ActiveChoices(models.TextChoices):
        INACTIVE = 'I'
        STAFF_ONLY = 'S'
        ACTIVE = 'A'

    ai_search_active = models.CharField(max_length=1, choices=ActiveChoices.choices, default=ActiveChoices.INACTIVE)
    ai_chat_active = models.CharField(max_length=1, choices=ActiveChoices.choices, default=ActiveChoices.INACTIVE)
    related_tours_active = models.CharField(max_length=1, choices=ActiveChoices.choices, default=ActiveChoices.INACTIVE)

    history = HistoricalRecords(excluded_fields=('active',))

    def get_caches_to_invalidate(self, previous):
        return "all"

    @property
    def logo_url(self):
        if self.logo:
            return self.logo.url
        else:
            return None

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.title == '':
                num_defaults = Settings.objects.filter(title__startswith='Default').count()
                if num_defaults == 0:
                    self.title = 'Default'
                else:
                    self.title = 'Default ' + str(num_defaults + 1)
        if self.active:
            Settings.objects.exclude(pk=self.pk).update(active=False)
        super(Settings, self).save(*args, **kwargs)

        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    @classmethod
    def load(cls) -> 'Settings':
        try:
            obj, _ = cls.objects.get_or_create(active=True)
        except cls.MultipleObjectsReturned:
            obj = cls.objects.filter(active=True).first()
            assert(obj is not None)
            cls.objects.filter(active=True).exclude(pk=obj.pk).update(active=False)
        return obj

    class Meta:
        verbose_name_plural = 'settings'

    def __str__(self):
        return self.title


class ContactSubmission(models.Model):
    from_email = models.EmailField()
    subject = models.CharField(max_length=400)
    message = models.TextField()
    time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)

    def get_caches_to_invalidate(self, previous):
        return []

    def __str__(self):
        return f'"{self.subject}" from {self.from_email}'

    def save(self, *args, **kwargs):
        if self.pk is None:
            super(ContactSubmission, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class BannerPhoto(models.Model):
    img = models.ImageField()
    min_AR = models.FloatField()
    max_AR = models.FloatField()
    active = models.BooleanField(default=True)
    history = HistoricalRecords(excluded_fields=('active',))

    def get_caches_to_invalidate(self, previous):
        return [reverse("front-page")]

    def __str__(self):
        return self.img.name


class PositionTemplate(models.Model):
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)

    def get_caches_to_invalidate(self, previous):
        tours = Tour.objects.filter(stops__template=self).distinct()
        tour_paths = [reverse("tour", args=[tour.slug]) for tour in tours]
        regions = Region.objects.all()
        region_paths = [reverse("tours", args=[region.slug]) for region in regions]
        return tour_paths + region_paths + [reverse("front-page"), reverse("destinations")]

    def __str__(self):
        return self.name


class Stop(models.Model):
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=100, null=True, blank=True)
    day = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(null=True)
    marked = models.BooleanField(default=True)
    arrow_break = models.BooleanField(default=True)
    text_x = models.FloatField(default=0)
    text_y = models.FloatField(default=0)
    prestrength = models.FloatField(default=1)
    poststrength = models.FloatField(default=1)
    template = models.ForeignKey(PositionTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    def get_caches_to_invalidate(self, previous):
        return [reverse("tour", args=[self.tour.slug])]

    def __str__(self):
        return f'Stop {self.name} in {self.tour}'

    class Meta:
        ordering = ['tour__name', 'order', 'day', 'name']


class MapPoint(models.Model):
    x = models.FloatField(blank=True, null=True)
    y = models.FloatField(blank=True, null=True)
    name = models.CharField(max_length=100)
    activation_radius = models.FloatField(default=1)
    size = models.FloatField(default=1)
    template = models.ForeignKey(PositionTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    # Validate that either x & y are both set or template is set
    def clean(self):
        if (self.x is None) != (self.y is None):
            raise ValidationError('Either both x and y must be set or template must be set')
        if self.template is not None and (self.x is not None or self.y is not None):
            raise ValidationError('Either both x and y must be set or template must be set')
        if self.template is None and (self.x is None or self.y is None):
            raise ValidationError('Either both x and y must be set or template must be set')

    def get_caches_to_invalidate(self, previous):
        region_tours = [reverse("tours", args=[region.slug]) for region in Region.objects.all()]
        return [reverse("front-page"), reverse("destinations")] + region_tours

    def __str__(self):
        return self.name


@receiver(post_save, sender=MapPoint)
@receiver(post_save, sender=Stop)
@receiver(post_save, sender=PositionTemplate)
def update_position_template(sender, instance, **kwargs):
    template = instance.template if hasattr(instance, 'template') else instance
    if template is not None and (template.x is None or template.y is None):
        map_points = template.mappoint_set.all()
        tour_stops = template.stop_set.all()
        if template.x is None:
            avg_x = 0
            x_count = 0
            for point in map_points:
                if point.x is not None:
                    avg_x += point.x
                    x_count += 1
            for stop in tour_stops:
                if stop.x is not None:
                    avg_x += stop.x
                    x_count += 1
            avg_x /= x_count
            template.x = avg_x
        if template.y is None:
            avg_y = 0
            y_count = 0
            for point in map_points:
                if point.y is not None:
                    avg_y += point.y
                    y_count += 1
            for stop in tour_stops:
                if stop.y is not None:
                    avg_y += stop.y
                    y_count += 1
            avg_y /= y_count
            template.y = avg_y
        template.save()


class HightlightBox(DraftHistory):
    title = models.CharField(max_length=100, blank=True, null=True)
    content = RichTextWithPlugins(blank=True, null=True)
    background_colour = ColorField(default='#FFFFFF')
    border_colour = ColorField(default='#FFFFFF')
    row = models.PositiveSmallIntegerField(default=1)
    col = models.PositiveSmallIntegerField(default=1)

    def get_caches_to_invalidate(self, previous):
        return [reverse("front-page")]

    def __str__(self):
        return self.title


class FileUpload(models.Model):
    name = models.CharField(max_length=200)
    file = models.FileField()
    slug = models.SlugField(unique=True)

    def get_caches_to_invalidate(self, previous):
        tours = self.tour_set.all()
        tour_paths = [reverse("tour", args=[tour.slug]) for tour in tours]
        return [self.get_absolute_url()] + tour_paths

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('view-doc', args=[self.slug])


class PageCache(models.Model):
    url = models.URLField()
    content = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['url'], name='url_idx'),
        ]


def purge_cloudflare_page(path):
    if not settings.PRODUCTION or settings.CLOUDFLARE_API_TOKEN is None:
        return
    purge_url = f'https://api.cloudflare.com/client/v4/zones/{settings.CLOUDFLARE_ZONE_ID}/purge_cache'
    headers = {
        'Authorization': f'Bearer {settings.CLOUDFLARE_API_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    data = {
        'files': [f'https://{settings.CLOUDFLARE_DOMAIN}{path}']
    }
    print(f'Purging {path} from Cloudflare using url: {purge_url}, headers: {headers}, data: {data}')
    response = requests.post(purge_url, headers=headers, data=json.dumps(data))
    print(f'Cloudflare response: {response.text}')
    if response.status_code != 200:
        raise Exception(f'Cloudflare purge of {path} failed with status code {response.status_code} and message {response.text}')


def purge_cloudflare_pages(paths):
    if not settings.PRODUCTION or settings.CLOUDFLARE_API_TOKEN is None:
        return
    purge_url = f'https://api.cloudflare.com/client/v4/zones/{settings.CLOUDFLARE_ZONE_ID}/purge_cache'
    headers = {
        'Authorization': f'Bearer {settings.CLOUDFLARE_API_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    data = {
        'files': [f'https://{settings.CLOUDFLARE_DOMAIN}{path}' for path in paths]
    }
    print(f'Purging {paths} from Cloudflare using url: {purge_url}, headers: {headers}, data: {data}')
    response = requests.post(purge_url, headers=headers, data=json.dumps(data))
    print(f'Cloudflare response: {response.text}')
    if response.status_code != 200:
        raise Exception(f'Cloudflare purge of {paths} failed with status code {response.status_code} and message {response.text}')


def invalidate_pages(pages_to_invalidate):
    if pages_to_invalidate == 'all':
        print('Invalidating all pages')
        # Purge all on cloudflare before deleting
        #for page in PageCache.objects.all():
            #page.delete()
        #for page in PageCache.objects.all():
            #purge_cloudflare_page(page.url)
        PageCache.objects.all().delete()
    else:
        print(f'Invalidating {pages_to_invalidate}')
        for page in pages_to_invalidate:
            # Remove all PageCaches that begin with the page
            for cache in PageCache.objects.filter(url__startswith=page):
                cache.delete()
        print(f'Invalidating {pages_to_invalidate} on Cloudflare')
        purge_cloudflare_page(pages_to_invalidate)


# Invalidate pagecache on model save
@receiver(post_save)
def invalidate_page_cache(sender, instance, **kwargs):
    if hasattr(instance, 'get_caches_to_invalidate'):
        pages_to_invalidate = instance.get_caches_to_invalidate(sender.objects.get(pk=instance.pk) if instance.pk else None)
        invalidate_pages(pages_to_invalidate)


class Testimonial(models.Model):
    name = models.CharField(max_length=200)
    quote = models.TextField()
    image = models.ImageField(upload_to='testimonials', null=True, blank=True)
    approved = models.BooleanField(default=False)
    added = models.DateTimeField(blank=True)
    country = CountryField(blank=True, null=True, blank_label='(select country)')
    age = models.PositiveIntegerField(blank=True, null=True)

    @classmethod
    def visible(cls, is_staff):
        if is_staff:
            return cls.objects.all()
        return cls.objects.filter(approved=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.added = timezone.now()
        super().save(*args, **kwargs)

    def get_caches_to_invalidate(self, previous):
        return [reverse("front-page")]

    @property
    def flag_url(self):
        return static(f'images/flags/{self.country.code.lower()}.svg')

    def __str__(self):
        return self.name
