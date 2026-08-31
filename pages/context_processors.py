from django.db.utils import OperationalError, ProgrammingError

from . import seo
from .models import (
    ProgramInitiative,
    SiteBranding,
    SitePageCopy,
    SitePageImages,
    SiteStat,
)


PROGRAM_NAV_PILLARS = (
    (
        ProgramInitiative.Pillar.CONFERENCES,
        "conferences",
        "Virtual Conferences",
        "Biannual gatherings under The Forge and The Hadassah Project.",
    ),
    (
        ProgramInitiative.Pillar.MENTORSHIP,
        "mentorship",
        "Mentorship Program",
        "Two-phase cohorts for guided growth and accountability.",
    ),
    (
        ProgramInitiative.Pillar.EVENTS,
        "events",
        "Events",
        "In-person gatherings and humanitarian outreach.",
    ),
)


def _site_branding():
    try:
        return SiteBranding.load()
    except (OperationalError, ProgrammingError):
        return SiteBranding()


def _page_images():
    try:
        return SitePageImages.load()
    except (OperationalError, ProgrammingError):
        return SitePageImages()


def _page_copy():
    try:
        return SitePageCopy.load()
    except (OperationalError, ProgrammingError):
        return SitePageCopy()


def site_globals(request):
    """Values available in every template."""
    branding = _site_branding()
    try:
        initiatives = list(
            ProgramInitiative.objects.filter(is_active=True).only(
                "pillar", "title", "slug", "eyebrow", "order"
            )
        )
    except (OperationalError, ProgrammingError):
        initiatives = []
    initiatives_by_pillar = {key: [] for key, *_ in PROGRAM_NAV_PILLARS}
    for initiative in initiatives:
        initiatives_by_pillar.setdefault(initiative.pillar, []).append(initiative)
    nav_program_pillars = [
        {
            "key": slug,
            "label": label,
            "description": description,
            "initiatives": initiatives_by_pillar[pillar],
        }
        for pillar, slug, label, description in PROGRAM_NAV_PILLARS
    ]
    try:
        site_stats = list(SiteStat.objects.all())
    except (OperationalError, ProgrammingError):
        site_stats = []

    page_images = _page_images()
    origin = request.build_absolute_uri("/").rstrip("/")

    # Preferred default social-share image: a real homepage photo first
    # (better previews than a small logo), falling back to the logo, then
    # nothing at all — pages never advertise a broken image URL.
    if page_images.home_hero:
        default_share_image = origin + page_images.home_hero.url
    elif branding.logo:
        default_share_image = origin + branding.logo.url
    else:
        default_share_image = ""

    return {
        "ORG_NAME": branding.display_name,
        "ORG_SHORT": branding.display_short_name,
        "ORG_TAGLINE": branding.display_tagline,
        "ORG_EMAIL": branding.display_email,
        "ORG_PHONE": branding.display_phone,
        "ORG_FOUNDED": branding.display_founded_year,
        "ORG_LOCATION": branding.display_location,
        "site_stats": site_stats,
        "site_branding": branding,
        "brand_palette": branding.color_palette_values,
        "nav_program_pillars": nav_program_pillars,
        "google_fonts_url": branding.google_fonts_url,
        "page_images": page_images,
        "page_copy": _page_copy(),
        "SITE_ORIGIN": origin,
        "DEFAULT_SHARE_IMAGE": default_share_image,
        "ORGANIZATION_JSONLD": seo.organization_jsonld(branding, origin),
    }
