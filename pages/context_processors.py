from django.db.utils import OperationalError, ProgrammingError

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
        "nav_program_pillars": nav_program_pillars,
        "google_fonts_url": branding.google_fonts_url,
        "page_images": _page_images(),
        "page_copy": _page_copy(),
    }
