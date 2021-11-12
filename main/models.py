from datetime import timedelta
from io import BytesIO

from PIL import Image
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.files import File
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Region(models.Model):
    name = models.CharField(max_length=40)
    slug = models.SlugField(primary_key=True)

    def __str__(self):
        return self.name


class Destination(models.Model):
    name = models.CharField(max_length=40)
    card_img = models.ImageField()
    slug = models.SlugField(unique=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, related_name='destinations')
    description = RichTextUploadingField(config_name='default')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['region', 'name']


class DestinationDetails(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField()
    content = RichTextUploadingField(config_name='default')
    order = models.IntegerField()
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='details')
    card_img = models.ImageField()

    class Meta:
        verbose_name_plural = 'Destination details'
        unique_together = [['destination', 'order'], ['destination', 'title'], ['destination', 'slug']]
        ordering = ['destination', 'order', 'slug']

    def __str__(self):
        return f'{self.title} for {self.destination.name}'


class Tour(models.Model):
    name = models.CharField(max_length=40)
    slug = models.SlugField()
    destinations = models.ManyToManyField(Destination, related_name='tours')
    start_date = models.DateField()
    end_date = models.DateField()
    description = RichTextUploadingField()
    excerpt = models.TextField()
    card_img = models.ImageField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def duration(self):
        return (self.end_date - self.start_date + timedelta(days=1)).days

    @property
    def close_tours(self):
        return sorted(Tour.objects.exclude(slug=self.slug), key=lambda tour: abs(tour.start_date - self.start_date))[:4]

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['start_date', 'price']


class ItineraryDay(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerary')
    title = models.CharField(max_length=100)
    day = models.IntegerField()
    body = RichTextUploadingField()

    class Meta:
        unique_together = [['tour', 'day']]
        ordering = ['tour', 'day']

    @property
    def date(self):
        return self.tour.start_date + timedelta(self.day - 1)

    def __str__(self):
        return f'{self.tour} day {self.day}'


class Article(models.Model):
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
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=NEWS)
    card_img = models.ImageField(null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['creation', 'title']


class Page(models.Model):
    slug = models.SlugField()
    title = models.CharField(max_length=40)
    content = RichTextUploadingField(config_name='default')
    card_img = models.ImageField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

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


@receiver(post_save)
def validate_image_size(sender, instance, created, **kwargs):
    if hasattr(instance, 'card_img'):
        image = Image.open(instance.card_img)
        (width, height) = image.size

        if width == 2 * height:
            return image
        elif width > 2 * height:
            new_height = height
            new_width = height * 2
        else:
            new_width = width
            new_height = width / 2

        crop_coords = (
        (width - new_width) / 2, (height - new_height) / 2, (width + new_width) / 2, (height + new_height) / 2)
        new_image = image.crop(crop_coords)

        img_io = BytesIO()
        new_image.save(img_io, format='JPEG')
        instance.card_img.save(instance.card_img.name, File(img_io))
