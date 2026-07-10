from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from datetime import UTC, timedelta
from urllib.parse import urlencode

from pages.models import Event
from oif_site import notify
from .forms import (ApplicationForm, ContactForm, EventRegistrationForm,
                    PartnerEnquiryForm, NewsletterForm)
from .models import EventRegistration, Application, NewsletterSubscriber


def _event_redirect(request, event):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return next_url
    return reverse("pages:event_detail", args=[event.slug])


def _event_end(event):
    return event.starts_at + timedelta(hours=2)


def _calendar_datetime(value):
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _calendar_description(event, event_url):
    parts = [
        event.summary or event.description or "Join this Onesimus Impact Foundation event.",
        "",
        f"Event details: {event_url}",
    ]
    if event.online_url:
        parts.append(f"Online access: {event.online_url}")
    if event.contact_email:
        parts.append(f"Contact: {event.contact_email}")
    return "\n".join(parts)


def _google_calendar_url(event, event_url):
    return "https://calendar.google.com/calendar/render?" + urlencode({
        "action": "TEMPLATE",
        "text": event.title,
        "dates": f"{_calendar_datetime(event.starts_at)}/{_calendar_datetime(_event_end(event))}",
        "details": _calendar_description(event, event_url),
        "location": event.venue_address or event.location,
        "sf": "true",
        "output": "xml",
    })


def _share_links(event, event_url):
    share_text = f"{event.title} - {event.summary or event.description or 'Join this OIF event.'}"
    return {
        "url": event_url,
        "title": event.title,
        "text": share_text,
        "whatsapp": "https://wa.me/?" + urlencode({"text": f"{share_text}\n{event_url}"}),
        "x": "https://twitter.com/intent/tweet?" + urlencode({
            "text": share_text,
            "url": event_url,
        }),
        "facebook": "https://www.facebook.com/sharer/sharer.php?" + urlencode({
            "u": event_url,
        }),
        "email": "mailto:?" + urlencode({
            "subject": event.title,
            "body": f"{share_text}\n\n{event_url}",
        }),
    }


def _ics_escape(value):
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.select_related("program"),
        slug=slug,
        is_published=True,
    )
    registration = None
    if request.user.is_authenticated:
        registration = EventRegistration.objects.filter(
            event=event, user=request.user
        ).first()
    related_events = (
        Event.objects.filter(is_published=True, starts_at__gte=event.starts_at)
        .exclude(pk=event.pk)
        .select_related("program")
        .order_by("starts_at")[:3]
    )
    event_url = request.build_absolute_uri(reverse("pages:event_detail", args=[event.slug]))
    return render(request, "engagement/event_detail.html", {
        "event": event,
        "registration": registration,
        "registration_form": EventRegistrationForm(instance=registration),
        "related_events": related_events,
        "calendar_links": {
            "google": _google_calendar_url(event, event_url),
            "apple": reverse("pages:event_calendar", args=[event.slug]),
        },
        "share_links": _share_links(event, event_url),
    })


def event_calendar(request, slug):
    event = get_object_or_404(Event, slug=slug, is_published=True)
    event_url = request.build_absolute_uri(reverse("pages:event_detail", args=[event.slug]))
    timestamp = _calendar_datetime(timezone.now())
    starts_at = _calendar_datetime(event.starts_at)
    ends_at = _calendar_datetime(_event_end(event))
    location = event.venue_address or event.location
    description = _calendar_description(event, event_url)
    ics = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Onesimus Impact Foundation//Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{event.slug}@onesimus-impact-foundation",
        f"DTSTAMP:{timestamp}",
        f"DTSTART:{starts_at}",
        f"DTEND:{ends_at}",
        f"SUMMARY:{_ics_escape(event.title)}",
        f"DESCRIPTION:{_ics_escape(description)}",
        f"LOCATION:{_ics_escape(location)}",
        f"URL:{_ics_escape(event_url)}",
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ])
    response = HttpResponse(ics, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{event.slug}.ics"'
    return response


@login_required
@require_POST
def register_event(request, slug):
    event = get_object_or_404(Event, slug=slug, is_published=True)
    redirect_to = _event_redirect(request, event)
    if not event.registration_open:
        messages.error(request, "Registration for this event is closed.")
        return redirect(redirect_to)
    if event.is_full:
        messages.error(request, "This event has reached capacity.")
        return redirect(redirect_to)

    form = EventRegistrationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please check the registration form and try again.")
        return redirect(redirect_to)

    defaults = form.cleaned_data
    reg, created = EventRegistration.objects.get_or_create(
        event=event, user=request.user,
        defaults=defaults,
    )
    if created:
        messages.success(request, f"You're registered for {event.title}.")
    else:
        for field, value in defaults.items():
            setattr(reg, field, value)
        if reg.status == EventRegistration.Status.CANCELLED:
            reg.status = EventRegistration.Status.REGISTERED
            messages.success(request, f"You're registered again for {event.title}.")
        else:
            messages.info(request, "Your event registration details have been updated.")
        reg.save()
    return redirect(redirect_to)


@login_required
@require_POST
def cancel_registration(request, pk):
    reg = get_object_or_404(EventRegistration, pk=pk, user=request.user)
    reg.status = EventRegistration.Status.CANCELLED
    reg.save(update_fields=["status"])
    messages.success(request, "Your registration has been cancelled.")
    return redirect("dashboard:events")


@login_required
def apply(request):
    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            app.save()
            notify.send_application_received(app)
            messages.success(
                request,
                f"Your {app.get_kind_display()} application has been submitted.")
            return redirect("dashboard:home")
    else:
        form = ApplicationForm()
    return render(request, "engagement/apply.html", {"form": form})


def contact(request):
    """Public contact form (Section 5.1.7 / 6.1)."""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()
            notify.send_contact_received(msg)
            messages.success(request, "Thank you — your message has been sent.")
            return redirect("pages:contact")
    else:
        form = ContactForm()
    return render(request, "pages/contact.html", {"form": form})


@require_POST
def partner_enquiry(request):
    """Public partner / sponsor interest form (Section 5.1.5)."""
    form = PartnerEnquiryForm(request.POST)
    if form.is_valid():
        enquiry = form.save()
        notify.send_partner_received(enquiry)
        messages.success(request, "Thank you — our partnerships team will be in touch.")
    else:
        messages.error(request, "Please check the partnership form and try again.")
    return redirect("pages:involved")


@require_POST
def newsletter_signup(request):
    """Footer newsletter sign-up (Section 6.8)."""
    form = NewsletterForm(request.POST)
    if form.is_valid():
        NewsletterSubscriber.objects.update_or_create(
            email=form.cleaned_data["email"],
            defaults={"name": form.cleaned_data.get("name", ""),
                      "is_active": True})
        messages.success(request, "You're subscribed to OIF updates.")
    else:
        messages.error(request, "Please enter a valid email address.")
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect("pages:home")
