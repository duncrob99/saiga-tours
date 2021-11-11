from datetime import timedelta

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models


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
    slug = models.SlugField(unique=True)
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
    title = models.CharField(max_length=40)
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
