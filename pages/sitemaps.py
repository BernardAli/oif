"""Sitemaps for basic technical SEO (Section 30)."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Policy


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return ["pages:home", "pages:about", "pages:programs", "pages:impact",
                "pages:involved", "pages:donate", "pages:gallery",
                "pages:contact"]

    def location(self, item):
        return reverse(item)


class PolicySitemap(Sitemap):
    priority = 0.3
    changefreq = "monthly"

    def items(self):
        return Policy.objects.all()

    def location(self, obj):
        return reverse("pages:policy", args=[obj.kind])

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViewSitemap,
    "policies": PolicySitemap,
}
