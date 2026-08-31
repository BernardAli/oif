"""Sitemaps for comprehensive technical SEO (Section 30).

Every publicly reachable, indexable URL in the site is represented here:
the static marketing pages, the three programs pillars' dedicated
initiative pages, legacy program wings, public events, and policies.
Transactional/private paths (dashboard, accounts, donations checkout,
engagement form endpoints) are intentionally excluded and kept out of
search results via robots.txt and per-page <meta name="robots"> tags
instead — see pages/views.py:robots_txt and each template's
`robots_meta` block.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Event, Policy, Program, ProgramInitiative


class StaticViewSitemap(Sitemap):
    """Fixed marketing pages, prioritized by how central they are to the
    site's conversion paths (give, join, learn) rather than uniformly."""
    changefreq = "weekly"

    PRIORITIES = {
        "pages:home": 1.0,
        "pages:programs": 0.9,
        "pages:donate": 0.9,
        "pages:involved": 0.8,
        "pages:impact": 0.8,
        "pages:about": 0.7,
        "pages:leadership": 0.6,
        "pages:speakers": 0.6,
        "pages:gallery": 0.6,
        "pages:contact": 0.5,
    }

    def items(self):
        return list(self.PRIORITIES)

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.PRIORITIES[item]


class ProgramInitiativeSitemap(Sitemap):
    """Dedicated pillar pages: The Forge, Hadassah, Bloom 360, OCOI, etc."""
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ProgramInitiative.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("pages:initiative_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


class LegacyProgramSitemap(Sitemap):
    """Legacy program-wing pages that still carry linked events/gallery items."""
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return Program.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("pages:program_detail", args=[obj.wing])

    def lastmod(self, obj):
        return obj.updated_at


class EventSitemap(Sitemap):
    """Public event detail pages. Upcoming events are weighted higher and
    checked for freshness more often than events already in the past."""
    changefreq = "daily"

    def items(self):
        return Event.objects.filter(is_published=True)

    def location(self, obj):
        return reverse("pages:event_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at

    def priority(self, obj):
        return 0.7 if obj.starts_at >= timezone.now() else 0.4


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
    "program_initiatives": ProgramInitiativeSitemap,
    "programs": LegacyProgramSitemap,
    "events": EventSitemap,
    "policies": PolicySitemap,
}
