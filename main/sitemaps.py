from django.contrib.sitemaps import Sitemap
from .models import *


class TourSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Tour.objects.filter(DraftHistory.published_q)

    def lastmod(self, obj: Tour):
        return obj.last_modified


class PageSitemap(Sitemap):
    changefreq = "monthly"

    def items(self):
        return Page.objects.filter(DraftHistory.published_q, in_navbar=True)

    def lastmod(self, obj: Page):
        return obj.last_mod

    def priority(self, obj: Page):
        return round(0.8 - obj.level * 0.1, 1)


class ArticleSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Article.objects.filter(DraftHistory.published_q)

    def lastmod(self, obj: Article):
        return obj.creation


class DetailsSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return DestinationDetails.all_published


class RegionToursMap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Region.all_published

    def location(self, item: Region):
        return reverse('tours', args=[item.slug])


class RegionGuidesMap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Region.all_published

    def location(self, item):
        return reverse('region', args=[item.slug])


class DestinationToursMap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Destination.all_published

    def location(self, item: Destination):
        return reverse('tours', args=[item.region.slug, item.slug])


class DestinationGuidesMap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Destination.all_published

    def location(self, item: Destination):
        return reverse('destination', args=[item.region.slug, item.slug])


class StaticPagesMap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return ['front-page', 'contact', 'destinations', 'tours', 'news', 'blog']

    def priority(self, item):
        if item == 'front-page':
            return 1
        elif item == 'contact':
            return 0.3
        elif item == 'destinations':
            return 0.7
        else:
            return 0.9

    def location(self, item):
        return reverse(item)
