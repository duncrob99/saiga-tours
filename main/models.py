from datetime import timedelta
from io import BytesIO
from typing import Tuple

from PIL import Image
from ckeditor_uploader.fields import RichTextUploadingField
from colorfield.fields import ColorField
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


def RichTextWithPlugins(*args, **kwargs):
    def plugin_path(name: str) -> str:
        return static(f'js/ckeditor/plugins/{name}/')

    def plugin_def(name: str) -> Tuple[str, str, str]:
        return name, plugin_path(name), 'plugin.js'

    field = RichTextUploadingField(external_plugin_resources=[
        plugin_def('splitsection'),
        plugin_def('imagefan')
    ], extra_plugins=['splitsection', 'imagefan'], *args, **kwargs)

    return field


class DraftHistoryManager(models.Manager):
    def all_published(self):
        return self.filter((Q(published_bool=True) & Q(published_date__isnull=True)) | Q(published_date__lte=timezone.now()))

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
        return cls.objects.filter((Q(published_bool=True) & Q(published_date__isnull=True)) | Q(published_date__lte=timezone.now()))

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

    def save(self, *args, **kwargs):
        super(Region, self).save(*args, **kwargs)
        if not settings.PRODUCTION:
            try:
                ping_google()
            except Exception as e:
                print(e)

    def __str__(self):
        return self.name


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
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True, blank=True)
    extensions = models.ManyToManyField('self', blank=True, symmetrical=False)
    display = models.BooleanField(default=True)
    keywords = models.TextField(null=True, blank=True)

    map_scale = models.FloatField(default=1)

    start_location = models.CharField(max_length=100, null=True, blank=True)
    end_location = models.CharField(max_length=100, null=True, blank=True)

    last_modified = models.DateTimeField(auto_now=True, null=True)

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

    def __str__(self):
        return self.title


class ItineraryDay(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerary')
    title = models.CharField(max_length=100, null=True, blank=True)
    day = models.IntegerField()
    body = RichTextWithPlugins(null=True, blank=True)
    history = HistoricalRecords()
    template = models.ForeignKey(ItineraryTemplate, on_delete=models.SET_NULL, null=True, blank=True)

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

    banner_img = models.ImageField(null=True, blank=True)
    banner_x = models.FloatField(null=True, blank=True)
    banner_y = models.FloatField(null=True, blank=True)

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
        ordering = ['-creation', 'title']

    def tag_list(self) -> str:
        return ' '.join([str(tag) for tag in self.tags.all()])

    def get_absolute_url(self):
        return reverse('article', args=[self.slug])


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
        return self.siblings.filter(published=True)

    @property
    def level(self):
        if self.parent is None:
            return 0
        else:
            return self.parent.level + 1

    def get_absolute_url(self):
        return '/' + self.full_path


@receiver(post_save)
def validate_image_size(sender, instance, created, **kwargs):
    if hasattr(instance, 'card_img'):
        with Image.open(instance.card_img) as image:
            format = image.format
            image = autorotate(image)
            ratio = 3 / 2
            (width, height) = image.size
            if abs(width - ratio * height) <= 5: # Prevents infinte loop when saving
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
    logo = models.ImageField(null=True, blank=True)
    twitter_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)
    facebook_link = models.URLField(blank=True, null=True)
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

    history = HistoricalRecords(excluded_fields=('active',))

    def save(self, *args, **kwargs):
        print(self.logo.url)
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
    def load(cls):
        obj, _ = cls.objects.get_or_create(active=True)
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

    def __str__(self):
        return self.img.name


class PositionTemplate(models.Model):
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)

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

    def __str__(self):
        return f'Stop {self.name} in {self.tour}'

    class Meta:
        ordering = ['tour__name', 'order', 'day', 'name']


class MapPoint(models.Model):
    x = models.FloatField()
    y = models.FloatField()
    name = models.CharField(max_length=100)
    activation_radius = models.FloatField(default=1)
    size = models.FloatField(default=1)
    template = models.ForeignKey(PositionTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class HightlightBox(DraftHistory):
    title = models.CharField(max_length=100, blank=True, null=True)
    content = RichTextWithPlugins(blank=True, null=True)
    background_colour = ColorField(default='#FFFFFF')
    border_colour = ColorField(default='#FFFFFF')
    row = models.PositiveSmallIntegerField(default=1)
    col = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.title


class FileUpload(models.Model):
    name = models.CharField(max_length=200)
    file = models.FileField()
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('view-doc', args=[self.slug])
