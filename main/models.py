from datetime import timedelta
from io import BytesIO

from PIL import Image
from ckeditor_uploader.fields import RichTextUploadingField
from colorfield.fields import ColorField
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import classproperty
from simple_history.models import HistoricalRecords


class DraftHistoryManager(models.Manager):
    def all_published(self):
        return self.filter(published=True)

    def visible(self, su: bool):
        return self.all() if su else self.all_published()


class DraftHistory(models.Model):
    history = HistoricalRecords(inherit=True, excluded_fields=['published'])
    published = models.BooleanField(default=False)
    objects = DraftHistoryManager()

    class Meta:
        abstract = True

    @classproperty
    def all_published(cls):
        return cls.objects.filter(published=True)

    @classmethod
    def visible(cls, su: bool):
        return cls.objects.all() if su else cls.all_published


class Region(DraftHistory):
    name = models.CharField(max_length=40)
    slug = models.SlugField(primary_key=True)
    tour_blurb = RichTextUploadingField(config_name='default')

    def __str__(self):
        return self.name


class Destination(DraftHistory):
    name = models.CharField(max_length=40)
    card_img = models.ImageField()
    slug = models.SlugField()
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, related_name='destinations')
    description = RichTextUploadingField(config_name='default')
    tour_blurb = RichTextUploadingField(config_name='default')
    map_colour = ColorField(null=True, blank=True)

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
    content = RichTextUploadingField(config_name='default')
    order = models.IntegerField()
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='details')
    type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    card_img = models.ImageField()
    linked_tours = models.ManyToManyField('Tour')

    class Meta:
        verbose_name_plural = 'Destination details'
        unique_together = [['destination', 'order', 'type'],
                           ['destination', 'title', 'type'],
                           ['destination', 'slug', 'type']]
        ordering = ['destination', 'order', 'slug']

    def __str__(self):
        return f'{self.title} for {self.destination.name}'


class State(models.Model):
    text = models.CharField(max_length=50, null=True, blank=True)
    color = ColorField(default=None, null=True, blank=True)
    text_color = ColorField(default=None, null=True, blank=True)
    border_color = ColorField(default=None, null=True, blank=True)
    priority = models.IntegerField(null=True, blank=True, help_text='0=top of list, 1 next, etc. Equivalent '
                                                                    'priorities will be sorted as per usual.')
    history = HistoricalRecords()

    def __str__(self):
        return self.text

    class Meta:
        ordering = ['priority', 'text']


class Tour(DraftHistory):
    name = models.CharField(max_length=40)
    slug = models.SlugField(unique=True)
    destinations = models.ManyToManyField(Destination, related_name='tours')
    start_date = models.DateField(null=True, blank=True)
    duration = models.IntegerField(null=True)
    description = RichTextUploadingField()
    excerpt = models.TextField()
    card_img = models.ImageField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True, blank=True)
    extensions = models.ManyToManyField('self', blank=True, symmetrical=False)
    display = models.BooleanField(default=True)

    start_location = models.CharField(max_length=100, null=True, blank=True)
    end_location = models.CharField(max_length=100, null=True, blank=True)

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

    def __str__(self):
        return self.name

    @property
    def priority(self):
        if self.state is not None:
            return self.state.priority
        else:
            return 9999 ** 9999

    class Meta:
        ordering = [F('state').asc(nulls_last=True), 'start_date', 'price']


class ItineraryDay(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerary')
    title = models.CharField(max_length=100)
    day = models.IntegerField()
    body = RichTextUploadingField()
    history = HistoricalRecords()

    class Meta:
        unique_together = [['tour', 'day']]
        ordering = [F('tour'), 'day']

    @property
    def date(self):
        return self.tour.start_date + timedelta(self.day - 1)

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
    blurb = RichTextUploadingField(config_name='default')

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
    title = models.CharField(max_length=40)
    creation = models.DateTimeField(auto_now_add=True)
    content = RichTextUploadingField(config_name='default')
    excerpt = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=NEWS)
    card_img = models.ImageField(null=True)
    keywords = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['creation', 'title']

    def tag_list(self) -> str:
        return ' '.join([str(tag) for tag in self.tags.all()])


class Page(DraftHistory):
    slug = models.SlugField()
    title = models.CharField(max_length=40)
    content = RichTextUploadingField(config_name='default')
    card_img = models.ImageField()
    banner_img = models.ImageField(null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    sibling_label = models.CharField(max_length=100, default='Extra')
    in_navbar = models.BooleanField(default=True)
    front_page_pos = models.IntegerField(null=True, blank=True)
    front_page_colour = ColorField(default='#FFFFFF')

    def __str__(self):
        return self.title

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
        return self.children.filter(published=True)

    @property
    def siblings(self):
        if self.parent is not None:
            return self.parent.children.exclude(pk=self.pk)
        else:
            return Page.objects.none()

    @property
    def published_siblings(self):
        return self.siblings.filter(published=True)


@receiver(post_save)
def validate_image_size(sender, instance, created, **kwargs):
    if hasattr(instance, 'card_img'):
        print(instance.card_img.path)
        image = Image.open(instance.card_img)
        (width, height) = image.size

        ratio = 3 / 2

        if abs(width - ratio * height) < 5:
            return image
        elif width > ratio * height:
            new_height = height
            new_width = height * ratio
        else:
            new_width = width
            new_height = width / ratio

        crop_coords = (
            (width - new_width) // 2, (height - new_height) // 2, (width + new_width) // 2, (height + new_height) // 2)
        new_image = image.crop(crop_coords)

        img_io = BytesIO()
        new_image.save(img_io, format=image.format)
        instance.card_img.save(instance.card_img.name, File(img_io))


class Settings(models.Model):
    title = models.CharField(max_length=30)
    active = models.BooleanField(default=False)
    accent_background = ColorField(default='#87cefa')
    accent_foreground = ColorField(default='#000000')
    accent_hover_background = ColorField(default='#87cefa')
    accent_hover_foreground = ColorField(default='#000000')
    site_title = models.CharField(max_length=50, default='Crowley Tours')
    catchphrase = models.CharField(max_length=50, default='We do cool tours')
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

    history = HistoricalRecords(excluded_fields=('active',))

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
    subject = models.CharField(max_length=100)
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


class SubscriptionSubmission(models.Model):
    email_address = models.EmailField(unique=True)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email_address

    def save(self, *args, **kwargs):
        if self.pk is None:
            super(SubscriptionSubmission, self).save(*args, **kwargs)


class BannerPhoto(models.Model):
    img = models.ImageField()
    min_AR = models.FloatField()
    max_AR = models.FloatField()
    active = models.BooleanField(default=True)
    history = HistoricalRecords(excluded_fields=('active',))

    def __str__(self):
        return self.img.name


class Stop(models.Model):
    x = models.FloatField()
    y = models.FloatField()
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=100)
    day = models.PositiveSmallIntegerField()
    order = models.PositiveSmallIntegerField(null=True)
    marked = models.BooleanField(default=True)
    text_x = models.FloatField(default=0)
    text_y = models.FloatField(default=0)

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

    def __str__(self):
        return self.name


class HightlightBox(DraftHistory):
    title = models.CharField(max_length=100, blank=True, null=True)
    content = RichTextUploadingField(blank=True, null=True)
    background_colour = ColorField(default='#FFFFFF')
    border_colour = ColorField(default='#FFFFFF')
    row = models.PositiveSmallIntegerField(default=1)
    col = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.title
