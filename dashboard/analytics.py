"""Analytics aggregations powering the ECharts dashboards.

Each function returns plain dicts/lists that serialise straight to JSON for
ECharts `option` objects on the client.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone

from donations.models import Donation
from engagement.models import EventRegistration, Application, MentorshipEnrollment
from accounts.models import User, Role


def _month_axis(months=12):
    """Return a list of (date, 'Mon YY') for the trailing `months` window."""
    today = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    out = []
    # walk back months-1 .. 0
    year, month = today.year, today.month
    seq = []
    for _ in range(months):
        seq.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    seq.reverse()
    for y, m in seq:
        out.append((f"{y}-{m:02d}", timezone.datetime(y, m, 1).strftime("%b %y")))
    return out


def donations_over_time(months=12, donor=None):
    axis = _month_axis(months)
    qs = Donation.objects.filter(status=Donation.Status.SUCCESS)
    if donor is not None:
        qs = qs.filter(donor=donor)
    rows = (qs.annotate(m=TruncMonth("created_at"))
              .values("m")
              .annotate(total=Coalesce(Sum("amount"),
                                       Decimal("0.00"),
                                       output_field=DecimalField()))
              .order_by("m"))
    lookup = {r["m"].strftime("%Y-%m"): float(r["total"]) for r in rows if r["m"]}
    return {
        "labels": [label for _, label in axis],
        "values": [lookup.get(key, 0.0) for key, _ in axis],
    }


def donations_by_channel():
    rows = (Donation.objects.filter(status=Donation.Status.SUCCESS)
            .values("channel")
            .annotate(total=Sum("amount"))
            .order_by("-total"))
    label = dict(Donation.Channel.choices)
    return [{"name": label[r["channel"]], "value": float(r["total"] or 0)}
            for r in rows]


def registrations_by_program():
    rows = (EventRegistration.objects
            .exclude(status=EventRegistration.Status.CANCELLED)
            .values("event__program__wing")
            .annotate(c=Count("id"))
            .order_by("-c"))
    from pages.models import Program
    wing_label = dict(Program.Wing.choices)
    labels, values = [], []
    for r in rows:
        wing = r["event__program__wing"]
        labels.append(wing_label.get(wing, "Other / General"))
        values.append(r["c"])
    return {"labels": labels, "values": values}


def member_growth(months=12):
    axis = _month_axis(months)
    rows = (User.objects.annotate(m=TruncMonth("date_joined"))
            .values("m").annotate(c=Count("id")).order_by("m"))
    lookup = {r["m"].strftime("%Y-%m"): r["c"] for r in rows if r["m"]}
    cumulative, running = [], 0
    # baseline: members who joined before the window
    first_key = axis[0][0] if axis else None
    if first_key:
        y, m = map(int, first_key.split("-"))
        boundary = timezone.datetime(y, m, 1, tzinfo=timezone.get_current_timezone())
        running = User.objects.filter(date_joined__lt=boundary).count()
    for key, _ in axis:
        running += lookup.get(key, 0)
        cumulative.append(running)
    return {"labels": [l for _, l in axis], "values": cumulative}


def applications_by_status():
    rows = (Application.objects.values("kind", "status")
            .annotate(c=Count("id")))
    kinds = dict(Application.Kind.choices)
    statuses = list(Application.Status.choices)
    matrix = {k: {s[0]: 0 for s in statuses} for k in kinds}
    for r in rows:
        matrix[r["kind"]][r["status"]] = r["c"]
    series = []
    for status_value, status_label in statuses:
        series.append({
            "name": status_label,
            "data": [matrix[k][status_value] for k in kinds],
        })
    return {"categories": [kinds[k] for k in kinds], "series": series}


def mentee_progress(mentor=None):
    qs = MentorshipEnrollment.objects.all()
    if mentor is not None:
        qs = qs.filter(mentor=mentor)
    buckets = {"Phase 1": 0, "Phase 2": 0, "Completed": 0}
    label = {"PHASE1": "Phase 1", "PHASE2": "Phase 2", "COMPLETE": "Completed"}
    for e in qs:
        buckets[label[e.phase]] += 1
    return [{"name": k, "value": v} for k, v in buckets.items()]


def org_summary():
    from pages.models import Event
    success = Donation.objects.filter(status=Donation.Status.SUCCESS)
    return {
        "total_raised": float(success.aggregate(t=Sum("amount"))["t"] or 0),
        "donation_count": success.count(),
        "member_count": User.objects.filter(role=Role.MEMBER).count(),
        "total_users": User.objects.count(),
        "active_events": Event.objects.filter(is_published=True).count(),
        "pending_applications": Application.objects.filter(
            status=Application.Status.PENDING).count(),
        "registrations": EventRegistration.objects.exclude(
            status=EventRegistration.Status.CANCELLED).count(),
        "mentorships": MentorshipEnrollment.objects.count(),
    }
