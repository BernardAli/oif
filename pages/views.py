from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from engagement.forms import PartnerEnquiryForm
from engagement.models import EventRegistration, MentorshipEnrollment
from .models import (Program, Speaker, TeamMember, Event, Testimonial,
                     GalleryImage, Policy)


def _leadership_context():
    return {
        "team_lead": TeamMember.objects.filter(
            position=TeamMember.Position.GLOBAL_LEAD).first(),
        "team_ed": TeamMember.objects.filter(
            position=TeamMember.Position.EXEC_DIRECTOR).first(),
        "directors": TeamMember.objects.filter(
            position=TeamMember.Position.DIRECTOR),
        "secretary": TeamMember.objects.filter(
            position=TeamMember.Position.SECRETARY).first(),
    }


def home(request):
    upcoming = (Event.objects.filter(is_published=True,
                                     starts_at__gte=timezone.now())
                .order_by("starts_at").first())
    ctx = {
        "programs": Program.objects.filter(is_active=True),
        "speakers": Speaker.objects.filter(featured=True)[:4],
        "upcoming_event": upcoming,
        "testimonials": Testimonial.objects.filter(is_published=True)[:3],
    }
    ctx.update(_leadership_context())
    return render(request, "pages/home.html", ctx)


def about(request):
    now = timezone.now()
    ctx = {
        "programs": Program.objects.filter(is_active=True),
        "featured_gallery": GalleryImage.objects.filter(is_published=True)[:6],
        "about_metrics": {
            "events": Event.objects.filter(is_published=True).count(),
            "registrations": EventRegistration.objects.exclude(
                status=EventRegistration.Status.CANCELLED
            ).count(),
            "mentorships": MentorshipEnrollment.objects.count(),
            "upcoming": Event.objects.filter(
                is_published=True, starts_at__gte=now
            ).count(),
        },
    }
    ctx.update(_leadership_context())
    return render(request, "pages/about.html", ctx)


def leadership(request):
    ctx = {
        "team_members": TeamMember.objects.all(),
    }
    ctx.update(_leadership_context())
    return render(request, "pages/leadership.html", ctx)


def speakers(request):
    return render(request, "pages/speakers.html", {
        "speakers": Speaker.objects.all(),
        "featured_speakers": Speaker.objects.filter(featured=True)[:4],
    })


def programs(request):
    ctx = {
        "programs": Program.objects.filter(is_active=True).prefetch_related("resources"),
        "upcoming_events": Event.objects.filter(
            is_published=True, starts_at__gte=timezone.now()),
        "past_events": Event.objects.filter(
            is_published=True, starts_at__lt=timezone.now())[:6],
    }
    return render(request, "pages/programs.html", ctx)


def program_detail(request, wing):
    program = get_object_or_404(
        Program.objects.prefetch_related("resources"),
        wing__iexact=wing,
        is_active=True,
    )
    related_events = Event.objects.filter(
        is_published=True,
        program=program,
    )
    now = timezone.now()
    ctx = {
        "program": program,
        "programs": Program.objects.filter(is_active=True).exclude(pk=program.pk),
        "upcoming_events": related_events.filter(starts_at__gte=now).order_by("starts_at")[:6],
        "past_events": related_events.filter(starts_at__lt=now).order_by("-starts_at")[:6],
    }
    return render(request, "pages/program_detail.html", ctx)


def impact(request):
    now = timezone.now()
    conf_attendees = EventRegistration.objects.filter(
        event__kind=Event.Kind.CONFERENCE).exclude(
        status=EventRegistration.Status.CANCELLED).count()
    mentorship_participants = MentorshipEnrollment.objects.count()
    cohorts = (MentorshipEnrollment.objects
               .exclude(cohort="")
               .values("cohort").annotate(n=Count("id")).order_by("-n"))
    ctx = {
        "speakers": Speaker.objects.all(),
        "conference_testimonials": Testimonial.objects.filter(
            is_published=True, source=Testimonial.Source.CONFERENCE),
        "mentorship_testimonials": Testimonial.objects.filter(
            is_published=True, source=Testimonial.Source.MENTORSHIP),
        "impact": {
            "conference_attendees": conf_attendees,
            "mentorship_participants": mentorship_participants,
            "cohorts": list(cohorts),
            "cohort_count": len(cohorts),
            "events_hosted": Event.objects.filter(starts_at__lt=now).count(),
        },
        "gallery": GalleryImage.objects.filter(is_published=True)[:8],
    }
    return render(request, "pages/impact.html", ctx)


def involved(request):
    return render(request, "pages/involved.html", {
        "partner_form": PartnerEnquiryForm(),
    })


def donate(request):
    return render(request, "pages/donate.html", {
        "donation_policy": Policy.objects.filter(
            kind=Policy.Kind.DONATION).first(),
    })


def gallery(request):
    return render(request, "pages/gallery.html", {
        "images": GalleryImage.objects.filter(is_published=True),
    })


def policy(request, kind):
    obj = get_object_or_404(Policy, kind=kind)
    return render(request, "pages/policy.html", {"policy": obj})


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /dashboard/",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
