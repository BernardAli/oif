from django.db.utils import OperationalError, ProgrammingError

from .models import Program, SiteBranding, SiteStat


def _site_branding():
    try:
        return SiteBranding.load()
    except (OperationalError, ProgrammingError):
        return SiteBranding()


def site_globals(request):
    """Values available in every template."""
    branding = _site_branding()
    try:
        nav_programs = list(
            Program.objects.filter(is_active=True).only(
                "wing", "tagline", "headline", "order"
            )
        )
    except (OperationalError, ProgrammingError):
        nav_programs = []
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
        "nav_programs": nav_programs,
        "google_fonts_url": branding.google_fonts_url,
    }
