from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from decimal import Decimal

from accounts.models import User, Role
from accounts.permissions import capability_required
from donations.models import Donation
from donations import paystack
from donations.views import _mark_success
from engagement.models import (EventRegistration, Application,
                               MentorshipEnrollment, ContactMessage,
                               PartnerEnquiry, NewsletterSubscriber)
from pages.models import (Event, Program, ProgramResource, SiteBranding,
                          SiteStat, Speaker, TeamMember, Testimonial,
                          GalleryImage, Policy)
from . import analytics
from .models import AuditLog, log_action
from .forms import (
    EventForm, MemberAdminForm, MentorshipEnrollmentForm, ProgramForm,
    ProgramResourceForm, SiteBrandingForm, SiteStatForm, SpeakerForm,
    TeamMemberForm, TestimonialForm, GalleryImageForm, PolicyForm,
)


def _paginate(request, queryset, param, per_page=20):
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.GET.get(param))
    params = request.GET.copy()
    params.pop(param, None)
    prefix = params.urlencode()
    page.query_prefix = f"{prefix}&" if prefix else ""
    return page


# --------------------------------------------------------------------------
# Dashboard home — content adapts to the user's role (role compliance)
# --------------------------------------------------------------------------
@login_required
def home(request):
    u = request.user
    ctx = {"summary": None, "my": {}}

    if u.can("view_org_analytics"):
        ctx["summary"] = analytics.org_summary()

    # Personal widgets shown to every role
    ctx["my"] = {
        "registrations": EventRegistration.objects.filter(user=u).exclude(
            status=EventRegistration.Status.CANCELLED).count(),
        "donated": sum(
            (d.amount for d in Donation.objects.filter(
                donor=u, status=Donation.Status.SUCCESS)),
            start=Decimal("0.00")),
        "applications": Application.objects.filter(user=u).count(),
    }
    if u.can("view_mentees"):
        ctx["my"]["mentees"] = MentorshipEnrollment.objects.filter(mentor=u).count()
    if u.role == Role.MEMBER or u.can("view_assignments"):
        ctx["my"]["my_mentorship"] = MentorshipEnrollment.objects.filter(
            mentee=u).first()

    ctx["upcoming_events"] = Event.objects.filter(
        is_published=True, starts_at__gte=timezone.now())[:3]
    return render(request, "dashboard/home.html", ctx)


# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------
def _event_detail_context(request, event):
    registrations_qs = (
        event.registrations
        .select_related("user")
        .order_by("status", "-created_at")
    )
    status_counts = dict(
        registrations_qs.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    registered = status_counts.get(EventRegistration.Status.REGISTERED, 0)
    attended = status_counts.get(EventRegistration.Status.ATTENDED, 0)
    cancelled = status_counts.get(EventRegistration.Status.CANCELLED, 0)
    active = registered + attended
    total = active + cancelled
    fill_rate = round(active / event.capacity * 100) if event.capacity else None
    attendance_rate = round(attended / active * 100) if active else 0

    role_labels = dict(Role.choices)
    role_rows = (
        registrations_qs.exclude(status=EventRegistration.Status.CANCELLED)
        .values("user__role")
        .annotate(c=Count("id"))
        .order_by("user__role")
    )
    role_mix = [
        {"label": role_labels.get(row["user__role"], row["user__role"]), "count": row["c"]}
        for row in role_rows
    ]
    timeline = (
        registrations_qs
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(c=Count("id"))
        .order_by("day")
    )
    timeline_rows = list(timeline)
    chart_data = {
        "status": [
            {"name": "Registered", "value": registered},
            {"name": "Attended", "value": attended},
            {"name": "Cancelled", "value": cancelled},
        ],
        "roles": [
            {"name": row["label"], "value": row["count"]}
            for row in role_mix
        ],
        "timeline": {
            "labels": [
                row["day"].strftime("%b %-d") if row["day"] else "Unknown"
                for row in timeline_rows
            ],
            "values": [row["c"] for row in timeline_rows],
        },
    }
    return {
        "event": event,
        "registrations": _paginate(request, registrations_qs, "registrations_page", 25),
        "status_choices": EventRegistration.Status.choices,
        "stats": {
            "registered": registered,
            "attended": attended,
            "cancelled": cancelled,
            "active": active,
            "total": total,
            "seats_left": event.seats_left,
            "fill_rate": fill_rate,
            "attendance_rate": attendance_rate,
        },
        "role_mix": role_mix,
        "timeline": timeline_rows,
        "chart_data": chart_data,
    }


@login_required
def events(request):
    u = request.user
    my_regs_qs = (EventRegistration.objects.filter(user=u)
                  .select_related("event").order_by("-created_at"))
    registered_ids = set(my_regs_qs.exclude(
        status=EventRegistration.Status.CANCELLED).values_list("event_id", flat=True))
    available_qs = Event.objects.filter(
        is_published=True, registration_open=True,
        starts_at__gte=timezone.now()).exclude(id__in=registered_ids)
    ctx = {"my_regs": _paginate(request, my_regs_qs, "my_regs_page", 20),
           "available": _paginate(request, available_qs, "available_page", 20),
           "can_manage": u.can("manage_events")}
    if u.can("manage_events"):
        now = timezone.now()
        events_qs = Event.objects.select_related("program")
        upcoming_qs = events_qs.filter(starts_at__gte=now).order_by("starts_at")
        archived_qs = events_qs.filter(starts_at__lt=now).order_by("-starts_at")
        ctx["upcoming_managed"] = _paginate(
            request, upcoming_qs, "upcoming_page", 20)
        ctx["archived_events"] = _paginate(
            request, archived_qs, "archived_page", 20)
        ctx["event_totals"] = {
            "upcoming": upcoming_qs.count(),
            "archived": archived_qs.count(),
            "open": events_qs.filter(registration_open=True, starts_at__gte=now).count(),
            "drafts": events_qs.filter(is_published=False).count(),
        }
    return render(request, "dashboard/events.html", ctx)


@capability_required("manage_events")
def event_detail(request, pk):
    event = get_object_or_404(Event.objects.select_related("program"), pk=pk)
    return render(request, "dashboard/event_detail.html", _event_detail_context(request, event))


@capability_required("manage_events")
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save()
            log_action(request.user, "event.create", event.title)
            messages.success(request, f"{event.title} has been created.")
            return redirect("dashboard:event_detail", pk=event.pk)
    else:
        form = EventForm()
    return render(request, "dashboard/event_form.html", {
        "form": form,
        "mode": "Create",
    })


@capability_required("manage_events")
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save()
            log_action(request.user, "event.update", event.title)
            messages.success(request, f"{event.title} has been updated.")
            return redirect("dashboard:event_detail", pk=event.pk)
    else:
        form = EventForm(instance=event)
    return render(request, "dashboard/event_form.html", {
        "form": form,
        "event": event,
        "mode": "Edit",
    })


@capability_required("manage_events")
def event_action(request, pk, action):
    event = get_object_or_404(Event, pk=pk)
    if request.method != "POST":
        return redirect("dashboard:event_detail", pk=event.pk)
    actions = {
        "open": ("registration_open", True, "Registration opened."),
        "close": ("registration_open", False, "Registration closed."),
        "publish": ("is_published", True, "Event published."),
        "unpublish": ("is_published", False, "Event unpublished."),
    }
    if action not in actions:
        raise PermissionDenied("Unknown event action.")
    field, value, message = actions[action]
    setattr(event, field, value)
    event.save(update_fields=[field])
    log_action(request.user, f"event.{action}", event.title)
    messages.success(request, message)
    return redirect("dashboard:event_detail", pk=event.pk)


@capability_required("manage_events")
def update_registration(request, event_pk, reg_pk):
    event = get_object_or_404(Event, pk=event_pk)
    reg = get_object_or_404(EventRegistration, pk=reg_pk, event=event)
    if request.method == "POST":
        status = request.POST.get("status")
        valid_statuses = {value for value, _ in EventRegistration.Status.choices}
        if status in valid_statuses:
            reg.status = status
            reg.save(update_fields=["status"])
            log_action(request.user, "registration.status",
                       f"{reg.user} @ {event.title}", status)
            messages.success(request, "Registration status updated.")
        else:
            messages.error(request, "Choose a valid registration status.")
    return redirect("dashboard:event_detail", pk=event.pk)


# --------------------------------------------------------------------------
# Donations
# --------------------------------------------------------------------------
@login_required
def donations_view(request):
    u = request.user
    my_donations = Donation.objects.filter(donor=u)
    scope = Donation.objects.all() if u.can("view_donations") else my_donations
    success_scope = scope.filter(status=Donation.Status.SUCCESS)
    monthly_rows = (
        success_scope.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    channel_rows = (
        success_scope.values("channel")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    campaign_rows = (
        success_scope.values("campaign")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:8]
    )
    status_counts = dict(
        scope.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    channel_labels = dict(Donation.Channel.choices)
    chart_data = {
        "monthly": {
            "labels": [row["month"].strftime("%b %y") for row in monthly_rows],
            "values": [float(row["total"] or 0) for row in monthly_rows],
        },
        "channels": [
            {"name": channel_labels.get(row["channel"], row["channel"]),
             "value": float(row["total"] or 0)}
            for row in channel_rows
        ],
        "campaigns": {
            "labels": [row["campaign"] or "General Fund" for row in campaign_rows],
            "values": [float(row["total"] or 0) for row in campaign_rows],
        },
        "statuses": [
            {"name": "Successful", "value": status_counts.get(Donation.Status.SUCCESS, 0)},
            {"name": "Pending", "value": status_counts.get(Donation.Status.PENDING, 0)},
            {"name": "Failed", "value": status_counts.get(Donation.Status.FAILED, 0)},
        ],
    }
    ctx = {
        "my_donations": _paginate(request, my_donations, "my_page", 20),
        "chart_data": chart_data,
        "totals": {
            "raised": success_scope.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "count": success_scope.count(),
            "pending": scope.filter(status=Donation.Status.PENDING).count(),
            "recurring": scope.filter(is_recurring=True).count(),
        },
        "can_manage": u.can("manage_donations"),
    }
    if u.can("view_donations"):
        ctx["all_donations"] = _paginate(
            request, Donation.objects.select_related("donor"), "all_page", 25)
        ctx["pending_donations"] = Donation.objects.filter(
            status=Donation.Status.PENDING).select_related("donor")
        ctx["failed_donations"] = Donation.objects.filter(
            status=Donation.Status.FAILED).select_related("donor")
        ctx["pending_donations"] = _paginate(
            request, ctx["pending_donations"], "pending_page", 20)
        ctx["failed_donations"] = _paginate(
            request, ctx["failed_donations"], "failed_page", 20)
        ctx["can_view_all"] = True
    return render(request, "dashboard/donations.html", ctx)


@login_required
def donation_detail(request, pk):
    donation = get_object_or_404(Donation.objects.select_related("donor"), pk=pk)
    if donation.donor_id != request.user.pk and not request.user.can("view_donations"):
        raise PermissionDenied("You cannot view this donation.")
    return render(request, "dashboard/donation_detail.html", {
        "donation": donation,
        "can_manage": request.user.can("manage_donations"),
        "paystack_configured": paystack.is_configured(),
    })


@capability_required("manage_donations")
def donation_action(request, pk, action):
    donation = get_object_or_404(Donation, pk=pk)
    if request.method != "POST":
        return redirect("dashboard:donation_detail", pk=donation.pk)
    if action == "verify":
        if not paystack.is_configured():
            _mark_success(donation)
            log_action(request.user, "donation.verify", donation.reference, "demo")
            messages.success(request, "Demo verification marked this donation successful.")
            return redirect("dashboard:donation_detail", pk=donation.pk)
        try:
            data = paystack.verify_transaction(donation.reference)
        except paystack.PaystackError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:donation_detail", pk=donation.pk)
        if data.get("status") == "success":
            _mark_success(donation)
        else:
            donation.status = Donation.Status.FAILED
            donation.save(update_fields=["status"])
        log_action(request.user, "donation.verify", donation.reference,
                   donation.status)
        messages.success(request, "Paystack verification completed.")
        return redirect("dashboard:donation_detail", pk=donation.pk)

    status_map = {
        "mark-success": Donation.Status.SUCCESS,
        "mark-pending": Donation.Status.PENDING,
        "mark-failed": Donation.Status.FAILED,
    }
    if action not in status_map:
        raise PermissionDenied("Unknown donation action.")
    if status_map[action] == Donation.Status.SUCCESS:
        _mark_success(donation)
    else:
        donation.status = status_map[action]
        donation.save(update_fields=["status"])
    log_action(request.user, "donation.status", donation.reference,
               donation.status)
    messages.success(request, "Donation status updated.")
    return redirect("dashboard:donation_detail", pk=donation.pk)


# --------------------------------------------------------------------------
# Applications  (member: own; staff: review queue)
# --------------------------------------------------------------------------
@login_required
def applications_view(request):
    u = request.user
    ctx = {"my_apps": _paginate(
        request, Application.objects.filter(user=u), "my_apps_page", 12)}
    if u.can("manage_applications"):
        ctx["can_manage"] = True
        ctx["queue"] = _paginate(
            request, Application.objects.select_related("user").all(),
            "queue_page", 20)
    return render(request, "dashboard/applications.html", ctx)


@capability_required("manage_applications")
def review_application(request, pk, decision):
    app = get_object_or_404(Application, pk=pk)
    if request.method == "POST" and decision in ("approve", "reject"):
        if decision == "approve":
            app.status = Application.Status.APPROVED
            # Promote the member to the role they applied for.
            new_role = Role.MENTOR if app.kind == Application.Kind.MENTOR \
                else Role.VOLUNTEER
            if app.user.role in (Role.MEMBER, Role.APPLICANT):
                app.user.role = new_role
                app.user.save(update_fields=["role"])
        else:
            app.status = Application.Status.REJECTED
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.save()
        log_action(request.user, "application.review",
                   f"{app.get_kind_display()} — {app.user}", app.status)
        messages.success(request, f"Application {app.get_status_display().lower()}.")
    return redirect("dashboard:applications")


# --------------------------------------------------------------------------
# Mentorship
# --------------------------------------------------------------------------
@login_required
def mentorship_view(request):
    u = request.user
    ctx = {}
    ctx["my_enrollment"] = MentorshipEnrollment.objects.filter(mentee=u).first()
    if u.can("view_mentees"):
        ctx["mentees"] = _paginate(
            request,
            MentorshipEnrollment.objects.filter(mentor=u).select_related("mentee", "program"),
            "mentees_page",
            20,
        )
    if u.can("manage_mentorship"):
        ctx["all_enrollments"] = _paginate(
            request,
            MentorshipEnrollment.objects.select_related("mentee", "mentor", "program"),
            "enrollments_page",
            20,
        )
        ctx["can_manage"] = True
        ctx["pending_members"] = _paginate(
            request,
            User.objects.filter(
                role=Role.MEMBER,
                mentorships_as_mentee__isnull=True,
            ),
            "pending_members_page",
            20,
        )
    return render(request, "dashboard/mentorship.html", ctx)


@capability_required("manage_mentorship")
def mentorship_create(request):
    if request.method == "POST":
        form = MentorshipEnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save()
            messages.success(request, "Mentorship enrollment created.")
            return redirect("dashboard:mentorship_edit", pk=enrollment.pk)
    else:
        form = MentorshipEnrollmentForm()
    return render(request, "dashboard/mentorship_form.html", {
        "form": form, "mode": "Create",
    })


@capability_required("manage_mentorship")
def mentorship_edit(request, pk):
    enrollment = get_object_or_404(MentorshipEnrollment, pk=pk)
    if request.method == "POST":
        form = MentorshipEnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, "Mentorship enrollment updated.")
            return redirect("dashboard:mentorship_edit", pk=enrollment.pk)
    else:
        form = MentorshipEnrollmentForm(instance=enrollment)
    return render(request, "dashboard/mentorship_form.html", {
        "form": form, "mode": "Edit", "enrollment": enrollment,
    })


CONTENT_REGISTRY = {
    "branding": {
        "model": SiteBranding, "form": SiteBrandingForm, "label": "Project profile",
        "description": "Control identity, logos, contact details, social links, and typography.",
        "add_label": "Project profile",
        "singleton": True,
    },
    "programs": {
        "model": Program, "form": ProgramForm, "label": "Programs",
        "description": "Control public program wings, homepage program cards, and ordering.",
        "add_label": "Program",
    },
    "resources": {
        "model": ProgramResource, "form": ProgramResourceForm, "label": "Program resources",
        "description": "Attach downloadable files and external resources to public program pages.",
        "add_label": "Resource",
    },
    "speakers": {
        "model": Speaker, "form": SpeakerForm, "label": "Speakers",
        "description": "Control public speaker archive and featured homepage speakers.",
        "add_label": "Speaker",
    },
    "team": {
        "model": TeamMember, "form": TeamMemberForm, "label": "Leadership team",
        "description": "Control public team, directors, executive leadership, and governance cards.",
        "add_label": "Team member",
    },
    "stats": {
        "model": SiteStat, "form": SiteStatForm, "label": "Site stats",
        "description": "Control headline impact numbers across the public site.",
        "add_label": "Stat",
    },
    "testimonials": {
        "model": Testimonial, "form": TestimonialForm, "label": "Testimonials",
        "description": "Control conference and mentorship testimonials on the Impact page.",
        "add_label": "Testimonial",
    },
    "gallery": {
        "model": GalleryImage, "form": GalleryImageForm, "label": "Media gallery",
        "description": "Upload and manage public gallery images and captions.",
        "add_label": "Gallery image",
    },
    "policies": {
        "model": Policy, "form": PolicyForm, "label": "Policies",
        "description": "Edit privacy, terms, and donation policy text shown in the footer.",
        "add_label": "Policy",
    },
}


@capability_required("manage_content")
def content_view(request):
    branding = SiteBranding.load()
    published_gallery = GalleryImage.objects.filter(is_published=True).count()
    published_testimonials = Testimonial.objects.filter(is_published=True).count()
    placeholder_policies = Policy.objects.filter(is_placeholder=True).count()

    return render(request, "dashboard/content.html", {
        "sections": CONTENT_REGISTRY,
        "branding": branding,
        "programs": _paginate(request, Program.objects.all(), "programs_page", 15),
        "resources": _paginate(
            request, ProgramResource.objects.select_related("program"),
            "resources_page", 15),
        "speakers": _paginate(request, Speaker.objects.all(), "speakers_page", 15),
        "team_members": _paginate(request, TeamMember.objects.all(), "team_page", 15),
        "stats": _paginate(request, SiteStat.objects.all(), "stats_page", 15),
        "testimonials": _paginate(
            request, Testimonial.objects.all(), "testimonials_page", 15),
        "gallery": _paginate(request, GalleryImage.objects.all(), "gallery_page", 15),
        "policies": _paginate(request, Policy.objects.all(), "policies_page", 15),
        "totals": {
            "programs": Program.objects.count(),
            "resources": ProgramResource.objects.count(),
            "speakers": Speaker.objects.count(),
            "team": TeamMember.objects.count(),
            "stats": SiteStat.objects.count(),
            "testimonials": Testimonial.objects.count(),
            "gallery": GalleryImage.objects.count(),
            "policies": Policy.objects.count(),
            "events": Event.objects.count(),
        },
        "cms_health": {
            "active_programs": Program.objects.filter(is_active=True).count(),
            "published_gallery": published_gallery,
            "published_testimonials": published_testimonials,
            "placeholder_policies": placeholder_policies,
            "published_library": published_gallery + published_testimonials,
        },
    })


@capability_required("manage_content")
def content_create(request, section):
    config = CONTENT_REGISTRY.get(section)
    if not config:
        raise PermissionDenied("Unknown content section.")
    if config.get("singleton"):
        obj = config["model"].load()
        return redirect("dashboard:content_edit", section=section, pk=obj.pk)
    form_class = config["form"]
    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, f"content.create.{section}", str(obj))
            messages.success(request, f"{config['label']} item saved.")
            return redirect("dashboard:content_edit", section=section, pk=obj.pk)
    else:
        form = form_class()
    return render(request, "dashboard/content_form.html", {
        "form": form, "section": section, "config": config, "mode": "Create",
    })


@capability_required("manage_content")
def content_edit(request, section, pk):
    config = CONTENT_REGISTRY.get(section)
    if not config:
        raise PermissionDenied("Unknown content section.")
    if config.get("singleton"):
        obj = config["model"].load()
    else:
        obj = get_object_or_404(config["model"], pk=pk)
    form_class = config["form"]
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            log_action(request.user, f"content.update.{section}", str(obj))
            messages.success(request, f"{config['label']} item updated.")
            return redirect("dashboard:content_edit", section=section, pk=obj.pk)
    else:
        form = form_class(instance=obj)
    return render(request, "dashboard/content_form.html", {
        "form": form, "section": section, "config": config,
        "mode": "Edit", "object": obj,
    })


@capability_required("manage_content")
@require_POST
def content_delete(request, section, pk):
    if section != "gallery":
        raise PermissionDenied("Only gallery images can be deleted here.")

    image = get_object_or_404(GalleryImage, pk=pk)
    caption = image.caption or "Gallery image"
    file_name = image.image.name if image.image else ""
    storage = image.image.storage if image.image else None
    image.delete()

    if file_name and storage and not GalleryImage.objects.filter(image=file_name).exists():
        storage.delete(file_name)

    log_action(request.user, "content.delete.gallery", caption)
    messages.success(request, f"{caption} deleted from the gallery.")
    return redirect("dashboard:content")


# --------------------------------------------------------------------------
# Enquiries — contact messages + partner / sponsor interest
# --------------------------------------------------------------------------
@capability_required("manage_contact")
def enquiries_view(request):
    return render(request, "dashboard/enquiries.html", {
        "messages_list": _paginate(
            request, ContactMessage.objects.select_related("handled_by"),
            "messages_page", 20),
        "partners": _paginate(
            request, PartnerEnquiry.objects.select_related("handled_by"),
            "partners_page", 20),
        "subscribers": _paginate(
            request, NewsletterSubscriber.objects.all(), "subscribers_page", 25),
        "can_manage_partners": request.user.can("manage_partners"),
        "totals": {
            "new_messages": ContactMessage.objects.filter(
                status=ContactMessage.Status.NEW).count(),
            "new_partners": PartnerEnquiry.objects.filter(
                status=PartnerEnquiry.Status.NEW).count(),
            "subscribers": NewsletterSubscriber.objects.filter(
                is_active=True).count(),
        },
    })


@capability_required("manage_contact")
def message_action(request, pk, action):
    msg = get_object_or_404(ContactMessage, pk=pk)
    if request.method != "POST":
        return redirect("dashboard:enquiries")
    status_map = {
        "read": ContactMessage.Status.READ,
        "resolve": ContactMessage.Status.RESOLVED,
        "reopen": ContactMessage.Status.NEW,
    }
    if action not in status_map:
        raise PermissionDenied("Unknown enquiry action.")
    msg.status = status_map[action]
    msg.handled_by = request.user
    msg.save(update_fields=["status", "handled_by"])
    log_action(request.user, "enquiry.status", msg.name, msg.status)
    messages.success(request, "Enquiry updated.")
    return redirect("dashboard:enquiries")


@capability_required("manage_partners")
def partner_action(request, pk, action):
    enquiry = get_object_or_404(PartnerEnquiry, pk=pk)
    if request.method != "POST":
        return redirect("dashboard:enquiries")
    status_map = {
        "review": PartnerEnquiry.Status.IN_REVIEW,
        "engage": PartnerEnquiry.Status.ENGAGED,
        "close": PartnerEnquiry.Status.CLOSED,
        "reopen": PartnerEnquiry.Status.NEW,
    }
    if action not in status_map:
        raise PermissionDenied("Unknown partner action.")
    enquiry.status = status_map[action]
    enquiry.handled_by = request.user
    enquiry.save(update_fields=["status", "handled_by"])
    log_action(request.user, "partner.status", enquiry.organisation, enquiry.status)
    messages.success(request, "Partner enquiry updated.")
    return redirect("dashboard:enquiries")


# --------------------------------------------------------------------------
# Audit trail (Section 5.2.16 / 11.11)
# --------------------------------------------------------------------------
@capability_required("view_audit")
def audit_view(request):
    logs = _paginate(request, AuditLog.objects.select_related("actor"), "logs_page", 30)
    return render(request, "dashboard/audit.html", {
        "logs": logs,
        "total": AuditLog.objects.count(),
    })


# --------------------------------------------------------------------------
# Members  (staff only)
# --------------------------------------------------------------------------
def _member_payment_queryset(member):
    lookup = Q(donor=member)
    if member.email:
        lookup |= Q(donor_email__iexact=member.email)
    return Donation.objects.filter(lookup).select_related("donor")


@capability_required("manage_members")
def members_view(request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    members = User.objects.all()
    if q:
        members = members.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(username__icontains=q) | Q(email__icontains=q))
    if role:
        members = members.filter(role=role)
    role_counts = dict(
        User.objects.values("role").annotate(c=Count("id")).values_list("role", "c")
    )
    growth_rows = (
        User.objects.annotate(month=TruncMonth("date_joined"))
        .values("month").annotate(c=Count("id")).order_by("month")
    )
    donation_status_counts = dict(
        Donation.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    roles = list(Role.choices)
    chart_data = {
        "roles": [
            {"name": label, "value": role_counts.get(value, 0)}
            for value, label in roles
        ],
        "growth": {
            "labels": [row["month"].strftime("%b %y") for row in growth_rows],
            "values": [row["c"] for row in growth_rows],
        },
        "engagement": {
            "labels": ["Registrations", "Applications", "Mentorships", "Paystack gifts"],
            "values": [
                EventRegistration.objects.count(),
                Application.objects.count(),
                MentorshipEnrollment.objects.count(),
                Donation.objects.count(),
            ],
        },
        "payments": [
            {"name": "Successful", "value": donation_status_counts.get(Donation.Status.SUCCESS, 0)},
            {"name": "Pending", "value": donation_status_counts.get(Donation.Status.PENDING, 0)},
            {"name": "Failed", "value": donation_status_counts.get(Donation.Status.FAILED, 0)},
        ],
    }
    staff_members = User.objects.filter(role__in=[Role.ADMIN, Role.DIRECTOR, Role.MENTOR])
    payment_members = (
        User.objects.filter(donations__isnull=False)
        .annotate(gifts=Count("donations"), raised=Sum("donations__amount"))
        .distinct()
        .order_by("-raised")
    )
    engagement_rows = (
        User.objects.annotate(
            registrations_count=Count("registrations", distinct=True),
            applications_count=Count("applications", distinct=True),
            gifts_count=Count("donations", distinct=True),
        )
        .order_by("-registrations_count", "-applications_count", "-gifts_count")
    )
    return render(request, "dashboard/members.html", {
        "members": _paginate(request, members, "members_page", 25), "q": q, "role": role,
        "roles": roles,
        "chart_data": chart_data,
        "staff_members": _paginate(request, staff_members, "staff_page", 20),
        "payment_members": _paginate(request, payment_members, "payments_page", 20),
        "engagement_rows": _paginate(request, engagement_rows, "engagement_page", 20),
        "totals": {
            "users": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "staff": User.objects.filter(role__in=[Role.ADMIN, Role.DIRECTOR]).count(),
            "paystack_gifts": Donation.objects.count(),
        },
    })


@capability_required("manage_members")
def member_detail(request, pk):
    member = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = MemberAdminForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            before_role = User.objects.get(pk=member.pk).role
            form.save()
            if member.role != before_role:
                log_action(request.user, "member.role_change", member.username,
                           f"{before_role} → {member.role}")
            else:
                log_action(request.user, "member.update", member.username)
            messages.success(request, "Member profile updated.")
            return redirect("dashboard:member_detail", pk=member.pk)
    else:
        form = MemberAdminForm(instance=member)

    donations = _member_payment_queryset(member)
    successful_donations = donations.filter(status=Donation.Status.SUCCESS)
    monthly_rows = (
        successful_donations.annotate(month=TruncMonth("created_at"))
        .values("month").annotate(total=Sum("amount")).order_by("month")
    )
    donation_status_counts = dict(
        donations.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    chart_data = {
        "giving": {
            "labels": [row["month"].strftime("%b %y") for row in monthly_rows],
            "values": [float(row["total"] or 0) for row in monthly_rows],
        },
        "payments": [
            {"name": "Successful", "value": donation_status_counts.get(Donation.Status.SUCCESS, 0)},
            {"name": "Pending", "value": donation_status_counts.get(Donation.Status.PENDING, 0)},
            {"name": "Failed", "value": donation_status_counts.get(Donation.Status.FAILED, 0)},
        ],
    }
    registrations = _paginate(
        request, member.registrations.select_related("event"),
        "registrations_page", 20)
    applications = _paginate(
        request, member.applications.all(), "applications_page", 20)
    mentorships_as_mentee = member.mentorships_as_mentee.select_related("mentor", "program")
    mentorships_as_mentor = member.mentorships_as_mentor.select_related("mentee", "program")
    return render(request, "dashboard/member_detail.html", {
        "member": member,
        "form": form,
        "registrations": registrations,
        "applications": applications,
        "mentorships_as_mentee": mentorships_as_mentee,
        "mentorships_as_mentor": mentorships_as_mentor,
        "donations": _paginate(request, donations, "donations_page", 20),
        "chart_data": chart_data,
        "paystack_configured": paystack.is_configured(),
        "stats": {
            "registrations": member.registrations.count(),
            "applications": member.applications.count(),
            "gifts": donations.count(),
            "raised": successful_donations.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
        },
    })


# --------------------------------------------------------------------------
# Analytics JSON API — payload is gated by role capability
# --------------------------------------------------------------------------
@login_required
def analytics_api(request):
    u = request.user
    data = {"role": u.role, "panels": []}

    if u.can("view_org_analytics"):
        data["panels"] += [
            {"id": "donations_time", "type": "line", "title": "Donations raised (last 12 months, GHS)",
             "payload": analytics.donations_over_time()},
            {"id": "donations_channel", "type": "pie", "title": "Donations by channel",
             "payload": analytics.donations_by_channel()},
            {"id": "member_growth", "type": "line", "title": "Member growth (cumulative)",
             "payload": analytics.member_growth()},
            {"id": "regs_program", "type": "bar", "title": "Event registrations by program",
             "payload": analytics.registrations_by_program()},
            {"id": "apps_status", "type": "stacked_bar", "title": "Applications by status",
             "payload": analytics.applications_by_status()},
        ]

    if u.can("view_mentees"):
        data["panels"].append(
            {"id": "mentee_progress", "type": "pie", "title": "My mentees by phase",
             "payload": analytics.mentee_progress(mentor=u)})

    # Personal panel for every member
    data["panels"].append(
        {"id": "my_giving", "type": "line", "title": "My giving (last 12 months, GHS)",
         "payload": analytics.donations_over_time(donor=u)})

    return JsonResponse(data)
