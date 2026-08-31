from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from engagement.forms import PartnerEnquiryForm
from engagement.models import EventRegistration, MentorshipEnrollment
from . import seo
from .models import (ConferenceEdition, Event, GalleryImage,
                     InitiativeArchiveEntry, MentorshipSession,
                     MentorshipTrack, Policy, Program, ProgramInitiative,
                     SDGFocus, Speaker, TeamMember, Testimonial)


def _leadership_context(members=None):
    """Split team members by position from a single query instead of one
    filtered `.first()`/queryset per position (4 near-identical queries)."""
    if members is None:
        members = list(TeamMember.objects.all())
    by_position = {}
    for member in members:
        by_position.setdefault(member.position, []).append(member)

    def _first(position):
        return next(iter(by_position.get(position, [])), None)

    return {
        "team_lead": _first(TeamMember.Position.GLOBAL_LEAD),
        "team_ed": _first(TeamMember.Position.EXEC_DIRECTOR),
        "directors": by_position.get(TeamMember.Position.DIRECTOR, []),
        "secretary": _first(TeamMember.Position.SECRETARY),
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
    members = list(TeamMember.objects.all())
    ctx = {"team_members": members}
    ctx.update(_leadership_context(members))
    return render(request, "pages/leadership.html", ctx)


def speakers(request):
    return render(request, "pages/speakers.html", {
        "speakers": Speaker.objects.all(),
        "featured_speakers": Speaker.objects.filter(featured=True)[:4],
    })


def programs(request):
    initiatives = ProgramInitiative.objects.filter(is_active=True).order_by(
        "pillar", "order", "title"
    )
    by_pillar = {
        value: [item for item in initiatives if item.pillar == value]
        for value, _label in ProgramInitiative.Pillar.choices
    }
    ctx = {
        "programs": Program.objects.filter(is_active=True).prefetch_related("resources"),
        "conference_initiatives": by_pillar[ProgramInitiative.Pillar.CONFERENCES],
        "mentorship_initiatives": by_pillar[ProgramInitiative.Pillar.MENTORSHIP],
        "event_initiatives": by_pillar[ProgramInitiative.Pillar.EVENTS],
        "upcoming_events": Event.objects.filter(
            is_published=True, starts_at__gte=timezone.now()),
        "past_events": Event.objects.filter(
            is_published=True, starts_at__lt=timezone.now())[:6],
    }
    return render(request, "pages/programs.html", ctx)


def initiative_detail(request, slug):
    initiative = get_object_or_404(
        ProgramInitiative.objects.filter(is_active=True), slug=slug
    )
    ctx = {
        "initiative": initiative,
        "breadcrumbs_jsonld": seo.breadcrumb_jsonld(request, [
            ("Home", reverse("pages:home")),
            ("Programs", reverse("pages:programs")),
            (initiative.title, reverse("pages:initiative_detail", args=[initiative.slug])),
        ]),
    }
    if initiative.page_type == ProgramInitiative.PageType.CONFERENCE:
        editions = ConferenceEdition.objects.filter(
            initiative=initiative, is_published=True
        ).prefetch_related("speaker_flyers")
        ctx.update({
            "upcoming_editions": editions.filter(status=ConferenceEdition.Status.UPCOMING),
            "past_editions": editions.filter(status=ConferenceEdition.Status.PAST),
        })
    elif initiative.page_type == ProgramInitiative.PageType.MENTORSHIP:
        ctx.update({
            "sessions": MentorshipSession.objects.filter(
                initiative=initiative, is_published=True
            ),
            "tracks": MentorshipTrack.objects.filter(initiative=initiative),
        })
    else:
        ctx["archive_entries"] = InitiativeArchiveEntry.objects.filter(
            initiative=initiative, is_published=True
        )
        if initiative.page_type == ProgramInitiative.PageType.OUTREACH:
            ctx["sdg_focuses"] = SDGFocus.objects.filter(
                initiative=initiative, is_active=True
            )
    return render(request, "pages/initiative_detail.html", ctx)


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
    program_gallery = GalleryImage.objects.filter(
        is_published=True, program=program
    ).exclude(image="").exclude(image__isnull=True)[:6]
    now = timezone.now()
    ctx = {
        "program": program,
        "programs": Program.objects.filter(is_active=True).exclude(pk=program.pk),
        "upcoming_events": related_events.filter(starts_at__gte=now).order_by("starts_at")[:6],
        "past_events": related_events.filter(starts_at__lt=now).order_by("-starts_at")[:6],
        "program_gallery": program_gallery,
        "program_event_count": related_events.count(),
        "breadcrumbs_jsonld": seo.breadcrumb_jsonld(request, [
            ("Home", reverse("pages:home")),
            ("Programs", reverse("pages:programs")),
            (program.get_wing_display(), reverse("pages:program_detail", args=[program.wing])),
        ]),
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
    return render(request, "pages/policy.html", {
        "policy": obj,
        "breadcrumbs_jsonld": seo.breadcrumb_jsonld(request, [
            ("Home", reverse("pages:home")),
            (obj.title, reverse("pages:policy", args=[obj.kind])),
        ]),
    })


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /dashboard/",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        # Transactional/private paths: donation checkout, callback, webhook,
        # per-reference status pages, and form-submission-only endpoints.
        # None of this is content worth ranking, and status/reference pages
        # are effectively per-donor. Kept crawlable-but-noindex on the pages
        # themselves too (see each template's robots_meta block) so this is
        # defense in depth, not the only safeguard.
        "Disallow: /donations/",
        "Disallow: /engagement/",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def error_404(request, exception):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
