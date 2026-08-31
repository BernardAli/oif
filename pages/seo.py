"""Structured data (JSON-LD) and other SEO helpers shared across apps.

Centralizing this here keeps view functions focused on request handling,
the same separation already used for dashboard/reporting.py and
dashboard/accounting.py.
"""
import json


def _dump(data):
    """Serialize a dict for embedding inside a <script type="application/ld+json">
    tag. `</` is escaped so no field value can prematurely close the
    surrounding <script> tag."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def organization_jsonld(branding, origin):
    """schema.org NGO record for the organization, used site-wide."""
    same_as = [
        url for url in (
            branding.facebook_url, branding.instagram_url, branding.twitter_url,
            branding.linkedin_url, branding.youtube_url,
        ) if url
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "NGO",
        "name": branding.display_name,
        "alternateName": branding.display_short_name,
        "url": origin + "/",
        "description": branding.footer_blurb,
        "foundingDate": branding.display_founded_year,
        "email": branding.display_email,
        "telephone": branding.display_phone,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": branding.display_location,
        },
    }
    if branding.logo:
        logo_url = origin + branding.logo.url
        data["logo"] = logo_url
        data["image"] = logo_url
    if same_as:
        data["sameAs"] = same_as
    return _dump(data)


def breadcrumb_jsonld(request, items):
    """`items` is an ordered iterable of (name, path) pairs. `path` may be a
    relative URL (resolved against the current request) or an absolute one."""
    element_list = [
        {
            "@type": "ListItem",
            "position": position,
            "name": name,
            "item": path if path.startswith("http") else request.build_absolute_uri(path),
        }
        for position, (name, path) in enumerate(items, start=1)
    ]
    return _dump({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": element_list,
    })


def event_jsonld(event, *, event_url, event_end, image_url, organizer_name, organizer_url):
    """schema.org Event record for one public event detail page."""
    if event.is_virtual:
        location = {"@type": "VirtualLocation", "url": event.online_url or event_url}
        attendance_mode = "https://schema.org/OnlineEventAttendanceMode"
    else:
        location = {"@type": "Place", "name": event.location}
        if event.venue_address:
            location["address"] = event.venue_address
        attendance_mode = "https://schema.org/OfflineEventAttendanceMode"
    data = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": event.title,
        "startDate": event.starts_at.isoformat(),
        "endDate": event_end.isoformat(),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": attendance_mode,
        "location": location,
        "description": (event.summary or event.description or event.title)[:500],
        "url": event_url,
        "organizer": {
            "@type": "Organization",
            "name": organizer_name,
            "url": organizer_url,
        },
    }
    if image_url:
        data["image"] = [image_url]
    return _dump(data)
