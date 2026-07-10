import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from decimal import Decimal

from accounts.models import User, Role
from accounts.permissions import capability_required
from donations.models import Donation
from donations import paystack
from donations.views import _mark_success, _payment_matches_donation
from engagement.models import (EventRegistration, Application,
                               MentorshipEnrollment, ContactMessage,
                               PartnerEnquiry, NewsletterSubscriber)
from pages.models import (Event, Program, ProgramResource, SiteBranding,
                          SiteStat, Speaker, TeamMember, Testimonial,
                          GalleryImage, Policy)
from . import analytics
from .reporting import (
    can_view_reports as _can_view_reports,
    cash_account_balance_map as _cash_account_balance_map,
    cash_account_rows as _cash_account_rows,
    month_key as _month_key,
    month_label as _month_label,
    report_period as _report_period,
    report_permissions as _report_permissions,
)
from .models import (AuditLog, CashAccount, CashMovement, Expense,
                     IntegrationSettings, MessageCampaign, MessageDelivery,
                     MessageTemplate, BankReconciliation, Budget, BudgetLine,
                     FiscalPeriod, Fund, JournalEntry, JournalLine,
                     LedgerAccount, log_action)
from .accounting import (ensure_accounting_defaults, financial_statements,
                         post_expense, post_journal, reverse_journal)
from .messaging import send_campaign
from .forms import (
    CashAccountForm, CashMovementForm, EventForm, ExpenseForm, MemberAdminForm,
    MentorshipEnrollmentForm, ProgramForm,
    ProgramResourceForm, SiteBrandingForm, SiteStatForm, SpeakerForm,
    TeamMemberForm, TestimonialForm, GalleryImageForm, PolicyForm,
    IntegrationSettingsForm, MessageCampaignForm, MessageTemplateForm,
    BankReconciliationForm, BudgetForm, BudgetLineFormSet, FiscalPeriodForm,
    FundForm, JournalEntryForm, JournalLineFormSet, LedgerAccountForm,
)


def _money_value(value):
    """Return a stable two-decimal representation for exports."""
    return f"{Decimal(str(value or 0)):.2f}"


@capability_required("view_message_reports")
def messaging_view(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    channel = request.GET.get("channel", "").strip()
    all_campaigns = MessageCampaign.objects.all()
    campaigns = (
        MessageCampaign.objects.select_related("created_by", "event")
        .annotate(
            deliveries_total=Count("deliveries"),
            deliveries_sent=Count(
                "deliveries", filter=Q(deliveries__status=MessageDelivery.Status.SENT)
            ),
            deliveries_failed=Count(
                "deliveries", filter=Q(deliveries__status=MessageDelivery.Status.FAILED)
            ),
        )
        .order_by("-created_at")
    )
    if q:
        campaigns = campaigns.filter(
            Q(title__icontains=q) | Q(subject__icontains=q)
            | Q(body__icontains=q) | Q(created_by__username__icontains=q)
        )
    if status:
        campaigns = campaigns.filter(status=status)
    if channel:
        campaigns = campaigns.filter(channel=channel)
    deliveries = MessageDelivery.objects.all()
    sent = deliveries.filter(status=MessageDelivery.Status.SENT).count()
    failed = deliveries.filter(status=MessageDelivery.Status.FAILED).count()
    skipped = deliveries.filter(status=MessageDelivery.Status.SKIPPED).count()
    attempted = sent + failed
    config = IntegrationSettings.load()
    sms_ready = bool(
        config.sms_enabled and (
            config.arkesel_api_key
            if config.sms_provider == IntegrationSettings.SmsProvider.ARKESEL
            else config.hubtel_client_id and config.hubtel_client_secret
        )
    )
    return render(request, "dashboard/messaging.html", {
        "campaigns": _paginate(request, campaigns, "campaigns_page", 20),
        "templates_count": MessageTemplate.objects.filter(is_active=True).count(),
        "templates": MessageTemplate.objects.all()[:8],
        "can_send": request.user.can("send_messages"),
        "can_configure": request.user.can("configure_integrations"),
        "q": q,
        "status": status,
        "channel": channel,
        "status_choices": MessageCampaign.Status.choices,
        "channel_choices": MessageCampaign.Channel.choices,
        "channel_status": {
            "email": config.email_enabled,
            "sms": sms_ready,
            "sms_provider": config.get_sms_provider_display(),
            "whatsapp": bool(
                config.whatsapp_enabled and config.whatsapp_access_token
                and config.whatsapp_phone_number_id
            ),
        },
        "recent_failures": deliveries.filter(
            status=MessageDelivery.Status.FAILED
        ).select_related("campaign")[:5],
        "totals": {
            "campaigns": all_campaigns.count(),
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "pending": deliveries.filter(status=MessageDelivery.Status.PENDING).count(),
            "delivery_rate": round(sent / attempted * 100) if attempted else 0,
        },
    })


@capability_required("send_messages")
def campaign_create(request):
    source_event = None
    if request.method == "POST":
        form = MessageCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            log_action(request.user, "messaging.campaign_create", campaign.title)
            if request.POST.get("action") == "send":
                result = send_campaign(campaign)
                log_action(request.user, "messaging.campaign_send", campaign.title, result)
                messages.success(request, f"Campaign processed: {result['sent']} sent, {result['failed']} failed, {result['skipped']} skipped.")
            else:
                messages.success(request, "Campaign saved as a draft.")
            return redirect("dashboard:campaign_detail", pk=campaign.pk)
    else:
        initial = {"channel": MessageCampaign.Channel.EMAIL}
        event_id = request.GET.get("event")
        if event_id:
            source_event = get_object_or_404(Event, pk=event_id)
            initial.update({
                "title": f"{source_event.title} update",
                "audience": MessageCampaign.Audience.EVENT,
                "event": source_event,
                "subject": f"Update: {source_event.title}",
                "body": (
                    "Hello {first_name},\n\n"
                    f"We have an update about {source_event.title}.\n\n"
                    "{org_name}"
                ),
            })
        form = MessageCampaignForm(initial=initial)
    config = IntegrationSettings.load()
    sms_ready = bool(
        config.sms_enabled and (
            config.arkesel_api_key
            if config.sms_provider == IntegrationSettings.SmsProvider.ARKESEL
            else config.hubtel_client_id and config.hubtel_client_secret
        )
    )
    return render(request, "dashboard/campaign_form.html", {
        "form": form,
        "source_event": source_event,
        "channel_status": {
            "email": config.email_enabled,
            "sms": sms_ready,
            "sms_provider": config.get_sms_provider_display(),
            "whatsapp": bool(
                config.whatsapp_enabled and config.whatsapp_access_token
                and config.whatsapp_phone_number_id
            ),
        },
        "audience_counts": {
            "all": User.objects.filter(is_active=True).count(),
            "marketing": User.objects.filter(
                is_active=True, marketing_opt_in=True
            ).count(),
            "newsletter": NewsletterSubscriber.objects.filter(is_active=True).count(),
        },
        "template_data": list(
            MessageTemplate.objects.filter(is_active=True).values(
                "id", "name", "subject", "body"
            )
        ),
    })


@capability_required("view_message_reports")
def campaign_detail(request, pk):
    campaign = get_object_or_404(MessageCampaign.objects.select_related("created_by", "event"), pk=pk)
    deliveries = campaign.deliveries.all()
    return render(request, "dashboard/campaign_detail.html", {
        "campaign": campaign,
        "deliveries": _paginate(request, deliveries, "deliveries_page", 30),
        "can_send": request.user.can("send_messages"),
        "counts": dict(deliveries.values("status").annotate(c=Count("id")).values_list("status", "c")),
    })


@capability_required("send_messages")
@require_POST
def campaign_send(request, pk):
    campaign = get_object_or_404(MessageCampaign, pk=pk)
    if campaign.status == MessageCampaign.Status.PROCESSING:
        messages.error(request, "This campaign is already processing.")
        return redirect("dashboard:campaign_detail", pk=pk)
    result = send_campaign(campaign)
    log_action(request.user, "messaging.campaign_send", campaign.title, result)
    messages.success(request, f"Campaign processed: {result['sent']} sent, {result['failed']} failed, {result['skipped']} skipped.")
    return redirect("dashboard:campaign_detail", pk=pk)


@capability_required("send_messages")
def message_template_create(request):
    return _management_form(
        request, form_class=MessageTemplateForm, mode="Create",
        config={"label": "Message Template", "description": "Create reusable Email, SMS, or WhatsApp content with recipient placeholders."},
        section="Messaging", back_url="dashboard:messaging",
        success_url="dashboard:message_template_edit", audit_action="messaging.template_create",
    )


@capability_required("send_messages")
def message_template_edit(request, pk):
    template = get_object_or_404(MessageTemplate, pk=pk)
    return _management_form(
        request, form_class=MessageTemplateForm, instance=template, mode="Edit",
        config={"label": template.name, "description": "Update reusable campaign content and availability."},
        section="Messaging", back_url="dashboard:messaging",
        success_url="dashboard:message_template_edit", audit_action="messaging.template_update",
    )


@capability_required("configure_integrations")
def integration_settings(request):
    config = IntegrationSettings.load()
    if request.method == "POST":
        form = IntegrationSettingsForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.updated_by = request.user
            config.save()
            log_action(request.user, "integrations.update", "Messaging and Paystack")
            messages.success(request, "Integration settings updated securely.")
            return redirect("dashboard:integration_settings")
    else:
        form = IntegrationSettingsForm(instance=config)
    sms_credentials_ready = bool(
        config.arkesel_api_key
        if config.sms_provider == IntegrationSettings.SmsProvider.ARKESEL
        else config.hubtel_client_id and config.hubtel_client_secret
    )
    paystack_config = paystack.configuration()
    return render(request, "dashboard/integration_settings.html", {
        "form": form,
        "config": config,
        "integration_status": {
            "sms": config.sms_enabled and sms_credentials_ready,
            "whatsapp": bool(
                config.whatsapp_enabled and config.whatsapp_access_token
                and config.whatsapp_phone_number_id
            ),
            "email": config.email_enabled,
            "paystack": paystack.is_configured(),
            "paystack_source": (
                "Site CMS" if config.paystack_use_cms_configuration else "Environment"
            ),
            "paystack_demo": paystack_config["demo_mode"],
        },
    })


def _paginate(request, queryset, param, per_page=20):
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.GET.get(param))
    params = request.GET.copy()
    params.pop(param, None)
    prefix = params.urlencode()
    page.query_prefix = f"{prefix}&" if prefix else ""
    return page


def _reports_context(request):
    period = _report_period(request)
    start, end = period["start"], period["end"]
    permissions = _report_permissions(request.user)
    context = {
        "period": period,
        "report_permissions": permissions,
        "chart_data": {},
    }

    if permissions["finance"]:
        success = Donation.objects.filter(
            status=Donation.Status.SUCCESS, created_at__date__gte=start,
            created_at__date__lte=end,
        )
        pending = Donation.objects.filter(
            status=Donation.Status.PENDING, created_at__date__gte=start,
            created_at__date__lte=end,
        )
        failed = Donation.objects.filter(
            status=Donation.Status.FAILED, created_at__date__gte=start,
            created_at__date__lte=end,
        )
        posted_expenses = Expense.objects.filter(
            status__in=[Expense.Status.APPROVED, Expense.Status.PAID],
            expense_date__gte=start, expense_date__lte=end,
        )
        finance_income = success.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        finance_expense = posted_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        donation_month_rows = (
            success.annotate(month=TruncMonth("created_at"))
            .values("month").annotate(total=Sum("amount"), count=Count("id"))
            .order_by("month")
        )
        expense_month_rows = (
            posted_expenses.annotate(month=TruncMonth("expense_date"))
            .values("month").annotate(total=Sum("amount"), count=Count("id"))
            .order_by("month")
        )
        income_lookup = {
            _month_key(row["month"]): row["total"] or Decimal("0.00")
            for row in donation_month_rows
        }
        expense_lookup = {
            _month_key(row["month"]): row["total"] or Decimal("0.00")
            for row in expense_month_rows
        }
        income_expense_rows = []
        for key in sorted(set(income_lookup) | set(expense_lookup)):
            if not key:
                continue
            income = income_lookup.get(key, Decimal("0.00"))
            expenses = expense_lookup.get(key, Decimal("0.00"))
            income_expense_rows.append({
                "label": _month_label(key),
                "income": income,
                "expenses": expenses,
                "net": income - expenses,
            })
        channel_labels = dict(Donation.Channel.choices)
        channel_rows = [
            {
                "label": channel_labels.get(row["channel"], row["channel"]),
                "count": row["count"],
                "total": row["total"] or Decimal("0.00"),
            }
            for row in success.values("channel")
            .annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
        ]
        campaign_rows = list(
            success.values("campaign")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")[:12]
        )
        cash_rows = _cash_account_rows(
            CashAccount.objects.order_by("status", "account_type", "name")
        )
        cash_balance = sum((row["balance"] for row in cash_rows), Decimal("0.00"))
        context["finance_report"] = {
            "income": finance_income,
            "expenses": finance_expense,
            "net": finance_income - finance_expense,
            "pending_amount": pending.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "failed_amount": failed.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "cash_balance": cash_balance,
            "successful_gifts": success.count(),
            "pending_count": pending.count(),
            "failed_count": failed.count(),
            "receipts_due": success.filter(receipt_sent=False).exclude(donor_email="").count(),
            "recurring": success.filter(is_recurring=True).count(),
            "income_expense_rows": income_expense_rows[-12:],
            "channel_rows": channel_rows,
            "campaign_rows": campaign_rows,
            "cash_rows": cash_rows[:8],
        }
        context["chart_data"]["finance_income_expense"] = {
            "labels": [row["label"] for row in income_expense_rows[-12:]],
            "income": [float(row["income"]) for row in income_expense_rows[-12:]],
            "expenses": [float(row["expenses"]) for row in income_expense_rows[-12:]],
            "net": [float(row["net"]) for row in income_expense_rows[-12:]],
        }
        context["chart_data"]["finance_channels"] = [
            {"name": row["label"], "value": float(row["total"])}
            for row in channel_rows
        ]
        accounting_budget = Budget.objects.filter(
            status__in=[Budget.Status.APPROVED, Budget.Status.LOCKED],
            fiscal_period__starts_on__lte=end,
            fiscal_period__ends_on__gte=start,
        ).select_related("fiscal_period", "fund").first()
        accounting_statements = financial_statements(
            start, end, budget=accounting_budget
        )
        operating_margin = (
            round(accounting_statements["surplus"] / accounting_statements["income"] * 100, 1)
            if accounting_statements["income"] else 0
        )
        current_ratio = (
            round(accounting_statements["assets"] / accounting_statements["liabilities"], 2)
            if accounting_statements["liabilities"] else None
        )
        context["accounting_report"] = {
            **accounting_statements,
            "budget": accounting_budget,
            "operating_margin": operating_margin,
            "current_ratio": current_ratio,
            "posted_journals": JournalEntry.objects.filter(
                status=JournalEntry.Status.POSTED,
                entry_date__gte=start, entry_date__lte=end,
            ).count(),
            "draft_journals": JournalEntry.objects.filter(
                status=JournalEntry.Status.DRAFT
            ).count(),
            "open_periods": FiscalPeriod.objects.filter(
                status=FiscalPeriod.Status.OPEN
            ).count(),
            "unreconciled": BankReconciliation.objects.filter(
                status=BankReconciliation.Status.DRAFT
            ).count(),
        }
        context["chart_data"]["accounting_accounts"] = {
            "labels": [row["code"] for row in accounting_statements["income_rows"] + accounting_statements["expense_rows"]],
            "values": [float(row["balance"]) for row in accounting_statements["income_rows"] + accounting_statements["expense_rows"]],
        }
        context["chart_data"]["budget_variance"] = {
            "labels": [row["account"].code for row in accounting_statements["budget_rows"]],
            "budget": [float(row["budget"]) for row in accounting_statements["budget_rows"]],
            "actual": [float(row["actual"]) for row in accounting_statements["budget_rows"]],
        }

    if permissions["events"]:
        events_qs = Event.objects.filter(starts_at__date__gte=start, starts_at__date__lte=end)
        registration_qs = EventRegistration.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        )
        attended = registration_qs.filter(status=EventRegistration.Status.ATTENDED).count()
        active_regs = registration_qs.exclude(status=EventRegistration.Status.CANCELLED).count()
        event_rows = (
            events_qs.annotate(
                registrations_count=Count(
                    "registrations",
                    filter=~Q(registrations__status=EventRegistration.Status.CANCELLED),
                    distinct=True,
                ),
                attended_count=Count(
                    "registrations",
                    filter=Q(registrations__status=EventRegistration.Status.ATTENDED),
                    distinct=True,
                ),
            )
            .select_related("program")
            .order_by("-starts_at")[:12]
        )
        program_labels = dict(Program.Wing.choices)
        program_rows = []
        for row in (
            registration_qs.exclude(status=EventRegistration.Status.CANCELLED)
            .values("event__program__wing")
            .annotate(count=Count("id"))
            .order_by("-count")
        ):
            wing = row["event__program__wing"]
            program_rows.append({
                "label": program_labels.get(wing, "General / Unassigned"),
                "count": row["count"],
            })
        event_kind_labels = dict(Event.Kind.choices)
        kind_rows = [
            {
                "label": event_kind_labels.get(row["kind"], row["kind"]),
                "count": row["count"],
            }
            for row in events_qs.values("kind").annotate(count=Count("id")).order_by("-count")
        ]
        context["events_report"] = {
            "events": events_qs.count(),
            "published": events_qs.filter(is_published=True).count(),
            "open_registration": events_qs.filter(registration_open=True).count(),
            "registrations": active_regs,
            "attended": attended,
            "attendance_rate": round((attended / active_regs) * 100) if active_regs else 0,
            "event_rows": event_rows,
            "program_rows": program_rows,
            "kind_rows": kind_rows,
        }
        context["chart_data"]["event_programs"] = {
            "labels": [row["label"] for row in program_rows],
            "values": [row["count"] for row in program_rows],
        }
        context["chart_data"]["event_kinds"] = [
            {"name": row["label"], "value": row["count"]} for row in kind_rows
        ]

    if permissions["people"]:
        users_qs = User.objects.filter(date_joined__date__gte=start, date_joined__date__lte=end)
        role_labels = dict(Role.choices)
        role_rows = [
            {
                "label": role_labels.get(row["role"], row["role"]),
                "count": row["count"],
            }
            for row in User.objects.values("role").annotate(count=Count("id")).order_by("-count")
        ]
        applications = Application.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        app_status_labels = dict(Application.Status.choices)
        app_kind_labels = dict(Application.Kind.choices)
        app_status_rows = [
            {"label": app_status_labels.get(row["status"], row["status"]), "count": row["count"]}
            for row in applications.values("status").annotate(count=Count("id")).order_by("-count")
        ]
        app_kind_rows = [
            {"label": app_kind_labels.get(row["kind"], row["kind"]), "count": row["count"]}
            for row in applications.values("kind").annotate(count=Count("id")).order_by("-count")
        ]
        phase_labels = dict(MentorshipEnrollment.Phase.choices)
        mentorship_rows = [
            {"label": phase_labels.get(row["phase"], row["phase"]), "count": row["count"]}
            for row in MentorshipEnrollment.objects.values("phase")
            .annotate(count=Count("id")).order_by("phase")
        ]
        context["people_report"] = {
            "new_users": users_qs.count(),
            "total_users": User.objects.count(),
            "members": User.objects.filter(role=Role.MEMBER).count(),
            "mentors": User.objects.filter(role=Role.MENTOR).count(),
            "volunteers": User.objects.filter(role=Role.VOLUNTEER).count(),
            "applications": applications.count(),
            "pending_applications": applications.filter(status=Application.Status.PENDING).count(),
            "mentorships": MentorshipEnrollment.objects.count(),
            "role_rows": role_rows,
            "app_status_rows": app_status_rows,
            "app_kind_rows": app_kind_rows,
            "mentorship_rows": mentorship_rows,
        }
        context["chart_data"]["people_roles"] = [
            {"name": row["label"], "value": row["count"]} for row in role_rows
        ]
        context["chart_data"]["applications_status"] = [
            {"name": row["label"], "value": row["count"]} for row in app_status_rows
        ]

    if permissions["content"]:
        program_rows = (
            Program.objects.annotate(
                resources_count=Count("resources", distinct=True),
                events_count=Count("events", distinct=True),
                gallery_count=Count("gallery", distinct=True),
            )
            .order_by("order", "wing")
        )
        content_totals = {
            "programs": Program.objects.count(),
            "active_programs": Program.objects.filter(is_active=True).count(),
            "resources": ProgramResource.objects.count(),
            "speakers": Speaker.objects.count(),
            "featured_speakers": Speaker.objects.filter(featured=True).count(),
            "leaders": TeamMember.objects.count(),
            "testimonials": Testimonial.objects.count(),
            "published_testimonials": Testimonial.objects.filter(is_published=True).count(),
            "gallery": GalleryImage.objects.count(),
            "published_gallery": GalleryImage.objects.filter(is_published=True).count(),
        }
        context["content_report"] = {
            "totals": content_totals,
            "program_rows": program_rows,
            "policy_placeholders": Policy.objects.filter(is_placeholder=True).count(),
        }
        context["chart_data"]["content_programs"] = {
            "labels": [program.get_wing_display() for program in program_rows],
            "values": [program.resources_count for program in program_rows],
        }

    if permissions["engagement"]:
        messages_qs = ContactMessage.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        partners_qs = PartnerEnquiry.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        newsletter_qs = NewsletterSubscriber.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        message_status_labels = dict(ContactMessage.Status.choices)
        partner_status_labels = dict(PartnerEnquiry.Status.choices)
        message_rows = [
            {"label": message_status_labels.get(row["status"], row["status"]), "count": row["count"]}
            for row in messages_qs.values("status").annotate(count=Count("id")).order_by("-count")
        ]
        partner_rows = [
            {"label": partner_status_labels.get(row["status"], row["status"]), "count": row["count"]}
            for row in partners_qs.values("status").annotate(count=Count("id")).order_by("-count")
        ]
        context["engagement_report"] = {
            "messages": messages_qs.count(),
            "new_messages": messages_qs.filter(status=ContactMessage.Status.NEW).count(),
            "partners": partners_qs.count(),
            "open_partners": partners_qs.exclude(status=PartnerEnquiry.Status.CLOSED).count(),
            "newsletter_signups": newsletter_qs.count(),
            "active_newsletter": NewsletterSubscriber.objects.filter(is_active=True).count(),
            "message_rows": message_rows,
            "partner_rows": partner_rows,
        }
        context["chart_data"]["engagement_messages"] = [
            {"name": row["label"], "value": row["count"]} for row in message_rows
        ]
        context["chart_data"]["engagement_partners"] = [
            {"name": row["label"], "value": row["count"]} for row in partner_rows
        ]

    if permissions["executive"]:
        context["executive_report"] = {
            "summary": analytics.org_summary(),
            "period_label": f"{start:%b %d, %Y} - {end:%b %d, %Y}",
        }

    return context


@login_required
def reports_view(request):
    if not _can_view_reports(request.user):
        raise PermissionDenied("Your role cannot access reports.")
    return render(request, "dashboard/reports.html", _reports_context(request))


@login_required
def reports_export(request):
    if not _can_view_reports(request.user):
        raise PermissionDenied("Your role cannot export reports.")
    ctx = _reports_context(request)
    requested = request.GET.get("type", "all")
    allowed = ctx["report_permissions"]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="oif-dashboard-reports.csv"'
    writer = csv.writer(response)
    writer.writerow(["section", "metric", "label", "value", "period_start", "period_end"])
    start, end = ctx["period"]["start"], ctx["period"]["end"]

    def include(name):
        return allowed.get(name) and requested in ("all", name)

    if include("executive") and ctx.get("executive_report"):
        for metric, value in ctx["executive_report"]["summary"].items():
            if metric == "total_raised":
                value = _money_value(value)
            writer.writerow(["executive", metric, "", value, start, end])
    if include("finance") and ctx.get("finance_report"):
        finance = ctx["finance_report"]
        for metric in (
            "income", "expenses", "net", "pending_amount", "failed_amount",
            "cash_balance", "successful_gifts", "receipts_due",
        ):
            value = finance[metric]
            if metric in {
                "income", "expenses", "net", "pending_amount",
                "failed_amount", "cash_balance",
            }:
                value = _money_value(value)
            writer.writerow(["finance", metric, "", value, start, end])
        for row in finance["income_expense_rows"]:
            writer.writerow(["finance", "monthly_net", row["label"], _money_value(row["net"]), start, end])
        for row in finance["channel_rows"]:
            writer.writerow(["finance", "channel", row["label"], _money_value(row["total"]), start, end])
        accounting = ctx.get("accounting_report")
        if accounting:
            for metric in ("income", "expenses", "surplus", "assets", "liabilities", "net_assets"):
                writer.writerow(["accounting", metric, "", _money_value(accounting[metric]), start, end])
            for row in accounting["trial_balance"]:
                writer.writerow(["accounting", "trial_balance", f"{row['code']} {row['name']}", _money_value(row["balance"]), start, end])
            for row in accounting["budget_rows"]:
                writer.writerow(["accounting", "budget_variance", str(row["account"]), _money_value(row["variance"]), start, end])
    if include("events") and ctx.get("events_report"):
        events = ctx["events_report"]
        for metric in ("events", "published", "open_registration", "registrations", "attended", "attendance_rate"):
            writer.writerow(["events", metric, "", events[metric], start, end])
        for row in events["program_rows"]:
            writer.writerow(["events", "registrations_by_program", row["label"], row["count"], start, end])
    if include("people") and ctx.get("people_report"):
        people = ctx["people_report"]
        for metric in ("new_users", "total_users", "members", "mentors", "volunteers", "applications", "pending_applications", "mentorships"):
            writer.writerow(["people", metric, "", people[metric], start, end])
        for row in people["role_rows"]:
            writer.writerow(["people", "role", row["label"], row["count"], start, end])
    if include("content") and ctx.get("content_report"):
        for metric, value in ctx["content_report"]["totals"].items():
            writer.writerow(["content", metric, "", value, start, end])
        writer.writerow(["content", "policy_placeholders", "", ctx["content_report"]["policy_placeholders"], start, end])
    if include("engagement") and ctx.get("engagement_report"):
        engagement = ctx["engagement_report"]
        for metric in ("messages", "new_messages", "partners", "open_partners", "newsletter_signups", "active_newsletter"):
            writer.writerow(["engagement", metric, "", engagement[metric], start, end])
        for row in engagement["message_rows"]:
            writer.writerow(["engagement", "message_status", row["label"], row["count"], start, end])
        for row in engagement["partner_rows"]:
            writer.writerow(["engagement", "partner_status", row["label"], row["count"], start, end])
    log_action(request.user, "reports.export", requested)
    return response


# --------------------------------------------------------------------------
# Dashboard home — content adapts to the user's role (role compliance)
# --------------------------------------------------------------------------
@login_required
def home(request):
    u = request.user
    now = timezone.now()
    ctx = {"summary": None, "my": {}, "work_queue": {}, "finance_summary": None}

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

    if u.can("manage_applications"):
        ctx["work_queue"]["pending_applications"] = Application.objects.filter(
            status=Application.Status.PENDING).count()
    if u.can("manage_events"):
        ctx["work_queue"]["open_events"] = Event.objects.filter(
            registration_open=True, starts_at__gte=now).count()
    if u.can("manage_contact"):
        ctx["work_queue"]["new_enquiries"] = ContactMessage.objects.filter(
            status=ContactMessage.Status.NEW).count()
    if u.can("manage_content"):
        ctx["work_queue"]["content_library"] = (
            Program.objects.count() + Speaker.objects.count() + TeamMember.objects.count()
        )
    if u.can("view_donations"):
        success = Donation.objects.filter(status=Donation.Status.SUCCESS)
        posted_expenses = Expense.objects.filter(
            status__in=[Expense.Status.APPROVED, Expense.Status.PAID]
        )
        raised = success.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        spent = posted_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        active_accounts = CashAccount.objects.filter(status=CashAccount.Status.ACTIVE)
        cash_balances = _cash_account_balance_map(active_accounts)
        ctx["finance_summary"] = {
            "raised": raised,
            "spent": spent,
            "net": raised - spent,
            "cash_balance": sum(cash_balances.values(), Decimal("0.00")),
            "cash_accounts": active_accounts.count(),
            "pending": Donation.objects.filter(status=Donation.Status.PENDING).count(),
            "failed": Donation.objects.filter(status=Donation.Status.FAILED).count(),
            "pending_expenses": Expense.objects.filter(status=Expense.Status.DRAFT).count(),
            "receipts_due": success.filter(receipt_sent=False).exclude(donor_email="").count(),
        }

    ctx["upcoming_events"] = (
        Event.objects.filter(is_published=True, starts_at__gte=now)
        .select_related("program")
        .annotate(active_registrations=Count(
            "registrations",
            filter=~Q(registrations__status=EventRegistration.Status.CANCELLED),
        ))
        .order_by("starts_at", "-created_at")[:5]
    )
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
    can_message = request.user.can("send_messages")
    event_campaigns = (
        MessageCampaign.objects.filter(event=event)
        .select_related("created_by")
        .annotate(
            delivery_count=Count("deliveries"),
            sent_count=Count(
                "deliveries", filter=Q(deliveries__status=MessageDelivery.Status.SENT)
            ),
            failed_count=Count(
                "deliveries", filter=Q(deliveries__status=MessageDelivery.Status.FAILED)
            ),
        )
        .order_by("-created_at")[:8]
    ) if request.user.can("view_message_reports") else MessageCampaign.objects.none()
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
        "can_message": can_message,
        "event_campaigns": event_campaigns,
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
@require_POST
def event_action(request, pk, action):
    event = get_object_or_404(Event, pk=pk)
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
@require_POST
def update_registration(request, event_pk, reg_pk):
    event = get_object_or_404(Event, pk=event_pk)
    reg = get_object_or_404(EventRegistration, pk=reg_pk, event=event)
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


@capability_required("view_donations")
def accounting_core(request):
    ensure_accounting_defaults()
    period = _report_period(request)
    fund_id = request.GET.get("fund", "")
    budget_id = request.GET.get("budget", "")
    fund = Fund.objects.filter(pk=fund_id).first() if fund_id else None
    budget = Budget.objects.filter(pk=budget_id).first() if budget_id else None
    statements = financial_statements(period["start"], period["end"], fund, budget)
    journals = JournalEntry.objects.select_related(
        "fiscal_period", "fund", "created_by", "approved_by"
    ).prefetch_related("lines")
    posted_donation_ids = JournalEntry.objects.filter(
        source_type="donation"
    ).values_list("source_id", flat=True)
    posted_expense_ids = JournalEntry.objects.filter(
        source_type="expense"
    ).values_list("source_id", flat=True)
    return render(request, "dashboard/accounting_core.html", {
        "period": period, "selected_fund": fund, "selected_budget": budget,
        "funds": Fund.objects.filter(is_active=True),
        "budgets": Budget.objects.select_related("fiscal_period", "fund"),
        "periods": FiscalPeriod.objects.all(),
        "accounts": LedgerAccount.objects.all(),
        "journals": _paginate(request, journals, "journals_page", 20),
        "reconciliations": BankReconciliation.objects.select_related("account")[:10],
        "statements": statements,
        "can_manage": request.user.can("manage_donations"),
        "health": {
            "unbalanced_drafts": sum(1 for j in JournalEntry.objects.filter(status=JournalEntry.Status.DRAFT).prefetch_related("lines") if not j.is_balanced),
            "open_periods": FiscalPeriod.objects.filter(status=FiscalPeriod.Status.OPEN).count(),
            "unreconciled": BankReconciliation.objects.filter(status=BankReconciliation.Status.DRAFT).count(),
            "chart_accounts": LedgerAccount.objects.filter(is_active=True).count(),
            "unposted_donations": Donation.objects.filter(
                status=Donation.Status.SUCCESS
            ).exclude(pk__in=posted_donation_ids).count(),
            "unposted_expenses": Expense.objects.filter(
                status__in=[Expense.Status.APPROVED, Expense.Status.PAID]
            ).exclude(pk__in=posted_expense_ids).count(),
        },
    })


def _accounting_setup_form(request, form_class, *, title, description, success="dashboard:accounting_core"):
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, "accounting.setup", str(obj))
            messages.success(request, f"{title} saved.")
            return redirect(success)
    else:
        form = form_class()
    return render(request, "dashboard/accounting_setup_form.html", {
        "form": form, "title": title, "description": description,
    })


@capability_required("manage_donations")
def ledger_account_create(request):
    return _accounting_setup_form(request, LedgerAccountForm, title="Ledger account", description="Add a posting or control account to the chart of accounts.")


@capability_required("manage_donations")
def fund_create(request):
    return _accounting_setup_form(request, FundForm, title="Fund", description="Track unrestricted and donor-restricted resources separately.")


@capability_required("manage_donations")
def fiscal_period_create(request):
    return _accounting_setup_form(request, FiscalPeriodForm, title="Fiscal period", description="Define a non-overlapping reporting and posting period.")


@capability_required("manage_donations")
@require_POST
def fiscal_period_action(request, pk, action):
    period = get_object_or_404(FiscalPeriod, pk=pk)
    if action == "close":
        if JournalEntry.objects.filter(fiscal_period=period, status=JournalEntry.Status.DRAFT).exists():
            messages.error(request, "Post or remove draft journals before closing this period.")
            return redirect("dashboard:accounting_core")
        period.status = FiscalPeriod.Status.CLOSED
        period.closed_by = request.user
        period.closed_at = timezone.now()
    elif action == "reopen":
        period.status = FiscalPeriod.Status.OPEN
        period.closed_by = None
        period.closed_at = None
    else:
        raise PermissionDenied("Unknown period action.")
    period.save(update_fields=["status", "closed_by", "closed_at"])
    log_action(request.user, f"accounting.period_{action}", period.name)
    messages.success(request, f"Fiscal period {action}d.")
    return redirect("dashboard:accounting_core")


@capability_required("manage_donations")
def journal_create(request):
    journal = JournalEntry(created_by=request.user)
    if request.method == "POST":
        form = JournalEntryForm(request.POST, instance=journal)
        lines = JournalLineFormSet(request.POST, instance=journal)
        if form.is_valid() and lines.is_valid():
            journal = form.save(commit=False)
            journal.created_by = request.user
            journal.save()
            lines.instance = journal
            lines.save()
            if request.POST.get("action") == "post":
                try:
                    post_journal(journal, request.user)
                    messages.success(request, "Balanced journal posted.")
                except ValidationError as exc:
                    journal.delete()
                    form.add_error(None, exc)
                else:
                    log_action(request.user, "accounting.journal_post", journal.number)
                    return redirect("dashboard:journal_detail", pk=journal.pk)
            else:
                log_action(request.user, "accounting.journal_create", journal.number)
                messages.success(request, "Journal saved as draft.")
                return redirect("dashboard:journal_detail", pk=journal.pk)
    else:
        form = JournalEntryForm(instance=journal)
        lines = JournalLineFormSet(instance=journal)
    return render(request, "dashboard/journal_form.html", {"form": form, "lines": lines})


@capability_required("view_donations")
def journal_detail(request, pk):
    journal = get_object_or_404(JournalEntry.objects.select_related("fund", "fiscal_period", "created_by", "approved_by"), pk=pk)
    return render(request, "dashboard/journal_detail.html", {
        "journal": journal, "can_manage": request.user.can("manage_donations"),
    })


@capability_required("manage_donations")
@require_POST
def journal_action(request, pk, action):
    journal = get_object_or_404(JournalEntry, pk=pk)
    try:
        if action == "post":
            post_journal(journal, request.user)
        elif action == "reverse":
            reverse_journal(journal, request.user)
        else:
            raise PermissionDenied("Unknown journal action.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        log_action(request.user, f"accounting.journal_{action}", journal.number)
        messages.success(request, f"Journal {action} completed.")
    return redirect("dashboard:journal_detail", pk=journal.pk)


@capability_required("manage_donations")
def budget_create(request):
    budget = Budget(created_by=request.user)
    if request.method == "POST":
        form = BudgetForm(request.POST, instance=budget)
        lines = BudgetLineFormSet(request.POST, instance=budget)
        if form.is_valid() and lines.is_valid():
            budget = form.save(commit=False)
            budget.created_by = request.user
            budget.save()
            lines.instance = budget
            lines.save()
            messages.success(request, "Budget saved.")
            return redirect("dashboard:accounting_core")
    else:
        form = BudgetForm(instance=budget)
        lines = BudgetLineFormSet(instance=budget)
    return render(request, "dashboard/budget_form.html", {"form": form, "lines": lines})


@capability_required("manage_donations")
@require_POST
def budget_action(request, pk, action):
    budget = get_object_or_404(Budget, pk=pk)
    status_map = {"approve": Budget.Status.APPROVED, "lock": Budget.Status.LOCKED, "draft": Budget.Status.DRAFT}
    if action not in status_map:
        raise PermissionDenied("Unknown budget action.")
    budget.status = status_map[action]
    budget.approved_by = request.user if budget.status != Budget.Status.DRAFT else None
    budget.save(update_fields=["status", "approved_by"])
    log_action(request.user, f"accounting.budget_{action}", budget.name)
    messages.success(request, "Budget status updated.")
    return redirect("dashboard:accounting_core")


@capability_required("manage_donations")
def reconciliation_create(request):
    if request.method == "POST":
        form = BankReconciliationForm(request.POST)
        if form.is_valid():
            reconciliation = form.save(commit=False)
            reconciliation.prepared_by = request.user
            reconciliation.save()
            messages.success(request, "Reconciliation saved for review.")
            return redirect("dashboard:accounting_core")
    else:
        form = BankReconciliationForm()
    return render(request, "dashboard/accounting_setup_form.html", {
        "form": form, "title": "Bank reconciliation",
        "description": "Compare book and adjusted statement balances before approval.",
    })


@capability_required("manage_donations")
@require_POST
def reconciliation_action(request, pk):
    reconciliation = get_object_or_404(BankReconciliation, pk=pk)
    if reconciliation.difference != 0:
        messages.error(request, "Reconciliation difference must be 0.00 before approval.")
    else:
        reconciliation.status = BankReconciliation.Status.RECONCILED
        reconciliation.approved_by = request.user
        reconciliation.reconciled_at = timezone.now()
        reconciliation.save(update_fields=["status", "approved_by", "reconciled_at"])
        reconciliation.account.statement_balance = reconciliation.statement_balance
        reconciliation.account.last_reconciled_on = reconciliation.statement_date
        reconciliation.account.save(update_fields=["statement_balance", "last_reconciled_on"])
        log_action(request.user, "accounting.reconcile", str(reconciliation))
        messages.success(request, "Account reconciliation approved.")
    return redirect("dashboard:accounting_core")


@capability_required("view_donations")
def finance_accounting(request):
    status = request.GET.get("status", "").strip()
    campaign = request.GET.get("campaign", "").strip()
    q = request.GET.get("q", "").strip()
    expense_status = request.GET.get("expense_status", "").strip()
    expense_category = request.GET.get("expense_category", "").strip()
    expense_q = request.GET.get("expense_q", "").strip()
    cash_q = request.GET.get("cash_q", "").strip()
    cash_type = request.GET.get("cash_type", "").strip()
    cash_status = request.GET.get("cash_status", "").strip()
    movement_account = request.GET.get("movement_account", "").strip()
    movement_status = request.GET.get("movement_status", "").strip()
    movement_q = request.GET.get("movement_q", "").strip()

    donations = Donation.objects.select_related("donor").order_by("-created_at")
    if status:
        donations = donations.filter(status=status)
    if campaign:
        donations = donations.filter(campaign=campaign)
    if q:
        donations = donations.filter(
            Q(reference__icontains=q) | Q(donor_name__icontains=q)
            | Q(donor_email__icontains=q) | Q(note__icontains=q)
        )

    success = Donation.objects.filter(status=Donation.Status.SUCCESS)
    pending = Donation.objects.filter(status=Donation.Status.PENDING)
    failed = Donation.objects.filter(status=Donation.Status.FAILED)
    expenses = Expense.objects.select_related(
        "recorded_by", "approved_by"
    ).order_by("-expense_date", "-created_at")
    if expense_status:
        expenses = expenses.filter(status=expense_status)
    if expense_category:
        expenses = expenses.filter(category=expense_category)
    if expense_q:
        expenses = expenses.filter(
            Q(title__icontains=expense_q) | Q(payee__icontains=expense_q)
            | Q(description__icontains=expense_q) | Q(reference__icontains=expense_q)
        )
    cash_accounts = CashAccount.objects.select_related("created_by").order_by(
        "status", "account_type", "name"
    )
    if cash_q:
        cash_accounts = cash_accounts.filter(
            Q(name__icontains=cash_q) | Q(institution_name__icontains=cash_q)
            | Q(account_number__icontains=cash_q) | Q(branch__icontains=cash_q)
            | Q(notes__icontains=cash_q)
        )
    if cash_type:
        cash_accounts = cash_accounts.filter(account_type=cash_type)
    if cash_status:
        cash_accounts = cash_accounts.filter(status=cash_status)
    cash_movements = CashMovement.objects.select_related(
        "account", "transfer_account", "linked_donation", "linked_expense",
        "recorded_by", "approved_by",
    ).order_by("-movement_date", "-created_at")
    if movement_account:
        cash_movements = cash_movements.filter(
            Q(account_id=movement_account) | Q(transfer_account_id=movement_account)
        )
    if movement_status:
        cash_movements = cash_movements.filter(status=movement_status)
    if movement_q:
        cash_movements = cash_movements.filter(
            Q(title__icontains=movement_q) | Q(counterparty__icontains=movement_q)
            | Q(reference__icontains=movement_q) | Q(memo__icontains=movement_q)
            | Q(account__name__icontains=movement_q)
        )
    posted_expenses = Expense.objects.filter(
        status__in=[Expense.Status.APPROVED, Expense.Status.PAID]
    )
    posted_movements = CashMovement.objects.filter(status=CashMovement.Status.POSTED)
    draft_expenses = Expense.objects.filter(status=Expense.Status.DRAFT)
    void_expenses = Expense.objects.filter(status=Expense.Status.VOID)
    status_counts = dict(
        Donation.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    expense_status_counts = dict(
        Expense.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    cash_status_counts = dict(
        CashMovement.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    channel_rows_raw = (
        success.values("channel")
        .annotate(total=Sum("amount"), gifts=Count("id"))
        .order_by("-total")
    )
    campaign_rows = (
        success.values("campaign")
        .annotate(total=Sum("amount"), gifts=Count("id"))
        .order_by("-total")[:10]
    )
    month_rows = (
        success.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("amount"), gifts=Count("id"))
        .order_by("month")
    )
    expense_month_rows = (
        posted_expenses.annotate(month=TruncMonth("expense_date"))
        .values("month")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("month")
    )
    income_lookup = {
        row["month"].strftime("%Y-%m"): row["total"] or Decimal("0.00")
        for row in month_rows if row["month"]
    }
    expense_lookup = {
        row["month"].strftime("%Y-%m"): row["total"] or Decimal("0.00")
        for row in expense_month_rows if row["month"]
    }
    month_keys = sorted(set(income_lookup) | set(expense_lookup))
    income_expense_rows = []
    for key in month_keys:
        year, month = map(int, key.split("-"))
        label = timezone.datetime(year, month, 1).strftime("%b %Y")
        income_total = income_lookup.get(key, Decimal("0.00"))
        expense_total = expense_lookup.get(key, Decimal("0.00"))
        income_expense_rows.append({
            "key": key,
            "label": label,
            "income": income_total,
            "expenses": expense_total,
            "net": income_total - expense_total,
        })
    expense_category_rows = (
        posted_expenses.values("category")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    all_cash_accounts = list(CashAccount.objects.order_by("status", "account_type", "name"))
    cash_account_balances = _cash_account_balance_map(all_cash_accounts)
    cash_account_rows = _cash_account_rows(cash_accounts)
    cash_type_labels = dict(CashAccount.AccountType.choices)
    cash_type_totals = {}
    for account in all_cash_accounts:
        label = cash_type_labels.get(account.account_type, account.account_type)
        cash_type_totals[label] = (
            cash_type_totals.get(label, Decimal("0.00"))
            + cash_account_balances.get(account.pk, Decimal("0.00"))
        )
    filtered_cash_balance = sum(
        (row["balance"] for row in cash_account_rows), Decimal("0.00")
    )
    filtered_statement_balance = sum(
        (row["account"].statement_balance or Decimal("0.00") for row in cash_account_rows),
        Decimal("0.00"),
    )
    category_labels = dict(Expense.Category.choices)
    channel_labels = dict(Donation.Channel.choices)
    chart_data = {
        "monthly": {
            "labels": [row["month"].strftime("%b %y") for row in month_rows if row["month"]],
            "values": [float(row["total"] or 0) for row in month_rows if row["month"]],
        },
        "channels": [
            {"name": channel_labels.get(row["channel"], row["channel"]),
             "value": float(row["total"] or 0)}
            for row in channel_rows_raw
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
        "income_expense": {
            "labels": [row["label"] for row in income_expense_rows],
            "income": [float(row["income"]) for row in income_expense_rows],
            "expenses": [float(row["expenses"]) for row in income_expense_rows],
            "net": [float(row["net"]) for row in income_expense_rows],
        },
        "expense_categories": [
            {"name": category_labels.get(row["category"], row["category"]),
             "value": float(row["total"] or 0)}
            for row in expense_category_rows
        ],
        "expense_statuses": [
            {"name": "Draft", "value": expense_status_counts.get(Expense.Status.DRAFT, 0)},
            {"name": "Approved", "value": expense_status_counts.get(Expense.Status.APPROVED, 0)},
            {"name": "Paid", "value": expense_status_counts.get(Expense.Status.PAID, 0)},
            {"name": "Void", "value": expense_status_counts.get(Expense.Status.VOID, 0)},
        ],
        "cash_accounts": [
            {"name": name, "value": float(total)}
            for name, total in cash_type_totals.items()
        ],
        "cash_statuses": [
            {"name": "Draft", "value": cash_status_counts.get(CashMovement.Status.DRAFT, 0)},
            {"name": "Posted", "value": cash_status_counts.get(CashMovement.Status.POSTED, 0)},
            {"name": "Void", "value": cash_status_counts.get(CashMovement.Status.VOID, 0)},
        ],
    }
    campaigns = (
        Donation.objects.exclude(campaign="")
        .values_list("campaign", flat=True)
        .distinct()
        .order_by("campaign")
    )
    month_close_rows = list(month_rows)[-6:]
    raised = success.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    spent = posted_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return render(request, "dashboard/finance_accounting.html", {
        "ledger": _paginate(request, donations, "ledger_page", 25),
        "expenses": _paginate(request, expenses, "expenses_page", 25),
        "cash_accounts": _paginate(request, cash_account_rows, "accounts_page", 12),
        "cash_movements": _paginate(request, cash_movements, "movements_page", 25),
        "pending_donations": _paginate(
            request, pending.select_related("donor"), "pending_page", 12),
        "failed_donations": _paginate(
            request, failed.select_related("donor"), "failed_page", 12),
        "campaign_rows": campaign_rows,
        "channel_rows": [
            {
                "label": channel_labels.get(row["channel"], row["channel"]),
                "gifts": row["gifts"],
                "total": row["total"],
            }
            for row in channel_rows_raw
        ],
        "expense_category_rows": [
            {
                "label": category_labels.get(row["category"], row["category"]),
                "count": row["count"],
                "total": row["total"],
            }
            for row in expense_category_rows
        ],
        "income_expense_rows": income_expense_rows[-12:],
        "month_close_rows": month_close_rows,
        "campaigns": campaigns,
        "status": status,
        "campaign": campaign,
        "q": q,
        "expense_status": expense_status,
        "expense_category": expense_category,
        "expense_q": expense_q,
        "cash_q": cash_q,
        "cash_type": cash_type,
        "cash_status": cash_status,
        "movement_account": movement_account,
        "movement_status": movement_status,
        "movement_q": movement_q,
        "status_choices": Donation.Status.choices,
        "expense_status_choices": Expense.Status.choices,
        "expense_category_choices": Expense.Category.choices,
        "cash_account_choices": CashAccount.objects.order_by("name"),
        "cash_type_choices": CashAccount.AccountType.choices,
        "cash_status_choices": CashAccount.Status.choices,
        "movement_status_choices": CashMovement.Status.choices,
        "movement_direction_choices": CashMovement.Direction.choices,
        "movement_category_choices": CashMovement.Category.choices,
        "chart_data": chart_data,
        "totals": {
            "raised": raised,
            "expenses": spent,
            "net": raised - spent,
            "cash_balance": sum(cash_account_balances.values(), Decimal("0.00")),
            "filtered_cash_balance": filtered_cash_balance,
            "cash_statement_balance": filtered_statement_balance,
            "cash_variance": filtered_cash_balance - filtered_statement_balance,
            "active_accounts": CashAccount.objects.filter(status=CashAccount.Status.ACTIVE).count(),
            "draft_movements": CashMovement.objects.filter(status=CashMovement.Status.DRAFT).count(),
            "posted_movements": posted_movements.count(),
            "pending_amount": pending.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "failed_amount": failed.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "draft_expense_amount": draft_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "void_expense_amount": void_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "draft_expenses": draft_expenses.count(),
            "receipts_due": success.filter(receipt_sent=False).exclude(donor_email="").count(),
            "recurring": Donation.objects.filter(is_recurring=True).count(),
            "success_count": success.count(),
        },
        "can_manage": request.user.can("manage_donations"),
    })


@capability_required("view_donations")
def finance_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="oif-income-expenditure.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "type", "date", "reference", "name", "email_or_payee", "category_or_campaign",
        "method_or_channel", "status", "currency", "income", "expense", "receipt",
    ])
    for donation in Donation.objects.order_by("-created_at"):
        writer.writerow([
            "income",
            donation.created_at.isoformat(),
            donation.reference,
            donation.donor_name,
            donation.donor_email,
            donation.campaign,
            donation.get_channel_display(),
            donation.get_status_display(),
            donation.currency,
            _money_value(donation.amount),
            "",
            "sent" if donation.receipt_sent else "due" if donation.donor_email else "no email",
        ])
    for expense in Expense.objects.order_by("-expense_date", "-created_at"):
        writer.writerow([
            "expense",
            expense.expense_date.isoformat(),
            expense.reference,
            expense.title,
            expense.payee,
            expense.get_category_display(),
            expense.payment_method,
            expense.get_status_display(),
            expense.currency,
            "",
            _money_value(expense.amount),
            expense.receipt.url if expense.receipt else "",
        ])
    for movement in CashMovement.objects.select_related(
        "account", "transfer_account"
    ).order_by("-movement_date", "-created_at"):
        writer.writerow([
            movement.direction.lower(),
            movement.movement_date.isoformat(),
            movement.reference,
            movement.title,
            movement.counterparty,
            movement.get_category_display(),
            movement.account.name,
            movement.get_status_display(),
            movement.currency,
            _money_value(movement.amount) if movement.direction == CashMovement.Direction.IN else "",
            _money_value(movement.amount) if movement.direction != CashMovement.Direction.IN else "",
            movement.attachment.url if movement.attachment else "",
        ])
    log_action(request.user, "finance.export", "Income and expenditure CSV")
    return response


@capability_required("manage_donations")
def cash_account_create(request):
    if request.method == "POST":
        form = CashAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.created_by = request.user
            account.save()
            if account.is_primary:
                CashAccount.objects.exclude(pk=account.pk).update(is_primary=False)
            log_action(request.user, "cash_account.create", account.name, account.status)
            messages.success(request, "Cash or bank account saved.")
            return redirect("dashboard:finance_accounting")
    else:
        form = CashAccountForm()
    return render(request, "dashboard/cash_account_form.html", {
        "form": form,
        "mode": "Create",
    })


@capability_required("manage_donations")
def cash_account_edit(request, pk):
    account = get_object_or_404(CashAccount, pk=pk)
    if request.method == "POST":
        form = CashAccountForm(request.POST, instance=account)
        if form.is_valid():
            account = form.save()
            if account.is_primary:
                CashAccount.objects.exclude(pk=account.pk).update(is_primary=False)
            log_action(request.user, "cash_account.update", account.name, account.status)
            messages.success(request, "Cash or bank account updated.")
            return redirect("dashboard:finance_accounting")
    else:
        form = CashAccountForm(instance=account)
    return render(request, "dashboard/cash_account_form.html", {
        "form": form,
        "account": account,
        "mode": "Edit",
    })


@capability_required("manage_donations")
@require_POST
def cash_account_action(request, pk, action):
    account = get_object_or_404(CashAccount, pk=pk)
    status_map = {
        "activate": CashAccount.Status.ACTIVE,
        "deactivate": CashAccount.Status.INACTIVE,
        "close": CashAccount.Status.CLOSED,
    }
    if action == "delete":
        name = account.name
        if account.movements.exists() or account.incoming_transfers.exists():
            messages.error(
                request,
                "Accounts with cash movements cannot be deleted. Close the account instead.",
            )
            return redirect("dashboard:finance_accounting")
        account.delete()
        log_action(request.user, "cash_account.delete", name)
        messages.success(request, f"{name} deleted.")
        return redirect("dashboard:finance_accounting")
    if action not in status_map:
        raise PermissionDenied("Unknown cash account action.")
    account.status = status_map[action]
    account.save(update_fields=["status", "updated_at"])
    log_action(request.user, "cash_account.status", account.name, account.status)
    messages.success(request, "Cash or bank account status updated.")
    return redirect("dashboard:finance_accounting")


@capability_required("manage_donations")
def cash_movement_create(request):
    if request.method == "POST":
        form = CashMovementForm(request.POST, request.FILES)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.recorded_by = request.user
            if movement.status == CashMovement.Status.POSTED:
                movement.approved_by = request.user
            movement.save()
            log_action(request.user, "cash_movement.create", movement.title, movement.status)
            messages.success(request, "Cash movement recorded.")
            return redirect("dashboard:finance_accounting")
    else:
        form = CashMovementForm()
    return render(request, "dashboard/cash_movement_form.html", {
        "form": form,
        "mode": "Create",
    })


@capability_required("manage_donations")
def cash_movement_edit(request, pk):
    movement = get_object_or_404(CashMovement, pk=pk)
    if request.method == "POST":
        form = CashMovementForm(request.POST, request.FILES, instance=movement)
        if form.is_valid():
            movement = form.save(commit=False)
            if movement.status == CashMovement.Status.POSTED and not movement.approved_by:
                movement.approved_by = request.user
            movement.save()
            log_action(request.user, "cash_movement.update", movement.title, movement.status)
            messages.success(request, "Cash movement updated.")
            return redirect("dashboard:finance_accounting")
    else:
        form = CashMovementForm(instance=movement)
    return render(request, "dashboard/cash_movement_form.html", {
        "form": form,
        "movement": movement,
        "mode": "Edit",
    })


@capability_required("manage_donations")
@require_POST
def cash_movement_action(request, pk, action):
    movement = get_object_or_404(CashMovement, pk=pk)
    status_map = {
        "post": CashMovement.Status.POSTED,
        "draft": CashMovement.Status.DRAFT,
        "void": CashMovement.Status.VOID,
    }
    if action == "delete":
        title = movement.title
        movement.delete()
        log_action(request.user, "cash_movement.delete", title)
        messages.success(request, "Cash movement deleted.")
        return redirect("dashboard:finance_accounting")
    if action not in status_map:
        raise PermissionDenied("Unknown cash movement action.")
    movement.status = status_map[action]
    if movement.status == CashMovement.Status.POSTED:
        movement.approved_by = request.user
    movement.save(update_fields=["status", "approved_by", "updated_at"])
    log_action(request.user, "cash_movement.status", movement.title, movement.status)
    messages.success(request, "Cash movement status updated.")
    return redirect("dashboard:finance_accounting")


@capability_required("manage_donations")
def expense_create(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            if expense.status in (Expense.Status.APPROVED, Expense.Status.PAID):
                expense.approved_by = request.user
            expense.save()
            log_action(request.user, "expense.create", expense.title, expense.status)
            messages.success(request, "Expense recorded.")
            return redirect("dashboard:finance_accounting")
    else:
        form = ExpenseForm()
    return render(request, "dashboard/expense_form.html", {
        "form": form,
        "mode": "Create",
    })


@capability_required("manage_donations")
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            expense = form.save(commit=False)
            if expense.status in (Expense.Status.APPROVED, Expense.Status.PAID) and not expense.approved_by:
                expense.approved_by = request.user
            expense.save()
            log_action(request.user, "expense.update", expense.title, expense.status)
            messages.success(request, "Expense updated.")
            return redirect("dashboard:finance_accounting")
    else:
        form = ExpenseForm(instance=expense)
    return render(request, "dashboard/expense_form.html", {
        "form": form,
        "expense": expense,
        "mode": "Edit",
    })


@capability_required("manage_donations")
@require_POST
def expense_action(request, pk, action):
    expense = get_object_or_404(Expense, pk=pk)
    status_map = {
        "approve": Expense.Status.APPROVED,
        "pay": Expense.Status.PAID,
        "draft": Expense.Status.DRAFT,
        "void": Expense.Status.VOID,
    }
    if action == "delete":
        title = expense.title
        expense.delete()
        log_action(request.user, "expense.delete", title)
        messages.success(request, "Expense deleted.")
        return redirect("dashboard:finance_accounting")
    if action not in status_map:
        raise PermissionDenied("Unknown expense action.")
    expense.status = status_map[action]
    if expense.status in (Expense.Status.APPROVED, Expense.Status.PAID):
        expense.approved_by = request.user
    expense.save(update_fields=["status", "approved_by", "updated_at"])
    if expense.status in (Expense.Status.APPROVED, Expense.Status.PAID):
        try:
            post_expense(expense, request.user)
        except ValidationError as exc:
            messages.warning(request, f"Expense updated, but accounting posting needs review: {'; '.join(exc.messages)}")
    log_action(request.user, "expense.status", expense.title, expense.status)
    messages.success(request, "Expense status updated.")
    return redirect("dashboard:finance_accounting")


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
@require_POST
def donation_action(request, pk, action):
    donation = get_object_or_404(Donation, pk=pk)
    if action == "verify":
        if not paystack.is_configured():
            if paystack.demo_mode():
                _mark_success(donation)
                log_action(request.user, "donation.verify", donation.reference, "demo")
                messages.success(request, "Demo verification marked this donation successful.")
            else:
                messages.error(request, "Paystack is not configured and demo mode is disabled.")
            return redirect("dashboard:donation_detail", pk=donation.pk)
        try:
            data = paystack.verify_transaction(donation.reference)
        except paystack.PaystackError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:donation_detail", pk=donation.pk)
        if data.get("status") == "success" and _payment_matches_donation(donation, data):
            _mark_success(donation)
        elif data.get("status") == "success":
            messages.error(
                request,
                "Paystack returned details that do not match this donation.",
            )
            return redirect("dashboard:donation_detail", pk=donation.pk)
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


@capability_required("manage_donations")
@require_POST
def donations_reconcile(request):
    if not paystack.is_configured():
        messages.error(request, "Configure and enable Paystack before reconciliation.")
        return redirect("dashboard:donations")
    confirmed = failed = unchanged = 0
    for donation in Donation.objects.filter(status=Donation.Status.PENDING).exclude(reference="")[:100]:
        try:
            data = paystack.verify_transaction(donation.reference)
        except paystack.PaystackError:
            failed += 1
            continue
        if data.get("status") == "success" and _payment_matches_donation(donation, data):
            _mark_success(donation)
            confirmed += 1
        else:
            unchanged += 1
    detail = {"confirmed": confirmed, "provider_errors": failed, "unchanged": unchanged}
    log_action(request.user, "donation.reconcile", "Pending donations", detail)
    messages.success(request, f"Reconciliation finished: {confirmed} confirmed, {unchanged} unchanged, {failed} provider errors.")
    return redirect("dashboard:donations")


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
@require_POST
def review_application(request, pk, decision):
    app = get_object_or_404(Application, pk=pk)
    if decision not in ("approve", "reject"):
        raise PermissionDenied("Unknown application decision.")
    if decision == "approve":
        app.status = Application.Status.APPROVED
        promotable_roles = {
            Application.Kind.MENTOR: Role.MENTOR,
            Application.Kind.VOLUNTEER: Role.VOLUNTEER,
        }
        new_role = promotable_roles.get(app.kind)
        if new_role and app.user.role in (Role.MEMBER, Role.APPLICANT):
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


MOVED_CONTENT_SECTIONS = {
    "programs": {
        "home": "dashboard:programs_manage",
        "create": "dashboard:program_create",
        "edit": "dashboard:program_edit",
    },
    "resources": {
        "home": "dashboard:resources_manage",
        "create": "dashboard:resource_create",
        "edit": "dashboard:resource_edit",
    },
    "speakers": {
        "home": "dashboard:speakers_manage",
        "create": "dashboard:speaker_create",
        "edit": "dashboard:speaker_edit",
    },
    "team": {
        "home": "dashboard:leadership_manage",
        "create": "dashboard:leadership_create",
        "edit": "dashboard:leadership_edit",
    },
}


def _content_redirect(section, pk=None, create=False):
    target = MOVED_CONTENT_SECTIONS.get(section)
    if not target:
        return None
    if create:
        return redirect(target["create"])
    if pk:
        return redirect(target["edit"], pk=pk)
    return redirect(target["home"])


def _management_form(request, *, form_class, instance=None, mode, config,
                     section, back_url, success_url, audit_action):
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, audit_action, str(obj))
            messages.success(request, f"{config['label']} saved.")
            return redirect(success_url, pk=obj.pk)
    else:
        form = form_class(instance=instance)
    return render(request, "dashboard/management_form.html", {
        "form": form,
        "object": instance,
        "mode": mode,
        "config": config,
        "section": section,
        "back_url": back_url,
    })


@capability_required("manage_content")
def programs_manage(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    programs = (
        Program.objects
        .annotate(
            resource_count=Count("resources", distinct=True),
            event_count=Count("events", distinct=True),
            gallery_count=Count("gallery", distinct=True),
        )
        .order_by("order", "wing")
    )
    if q:
        programs = programs.filter(
            Q(tagline__icontains=q) | Q(headline__icontains=q)
            | Q(description__icontains=q) | Q(wing__icontains=q)
        )
    if status == "active":
        programs = programs.filter(is_active=True)
    elif status == "hidden":
        programs = programs.filter(is_active=False)
    return render(request, "dashboard/programs_manage.html", {
        "programs": _paginate(request, programs, "programs_page", 12),
        "q": q,
        "status": status,
        "wing_choices": Program.Wing.choices,
        "totals": {
            "programs": Program.objects.count(),
            "active": Program.objects.filter(is_active=True).count(),
            "resources": ProgramResource.objects.count(),
            "events": Event.objects.filter(program__isnull=False).count(),
        },
    })


@capability_required("manage_content")
def program_create(request):
    return _management_form(
        request,
        form_class=ProgramForm,
        mode="Create",
        config={
            "label": "Program",
            "description": "Shape a public program wing, its positioning, imagery, order, and visibility.",
        },
        section="Programs",
        back_url="dashboard:programs_manage",
        success_url="dashboard:program_edit",
        audit_action="program.create",
    )


@capability_required("manage_content")
def program_edit(request, pk):
    program = get_object_or_404(Program, pk=pk)
    return _management_form(
        request,
        form_class=ProgramForm,
        instance=program,
        mode="Edit",
        config={
            "label": program.get_wing_display(),
            "description": "Update the public program story, card copy, media, order, and active state.",
        },
        section="Programs",
        back_url="dashboard:programs_manage",
        success_url="dashboard:program_edit",
        audit_action="program.update",
    )


@capability_required("manage_content")
@require_POST
def program_delete(request, pk):
    program = get_object_or_404(Program, pk=pk)
    name = program.get_wing_display()
    affected = {
        "resources": program.resources.count(),
        "events": program.events.count(),
        "gallery": program.gallery.count(),
        "mentorships": MentorshipEnrollment.objects.filter(program=program).count(),
    }
    program.delete()
    log_action(request.user, "program.delete", name)
    messages.success(
        request,
        (
            f"{name} deleted. Removed {affected['resources']} resources; "
            f"unlinked {affected['events']} events, {affected['gallery']} gallery "
            f"items, and {affected['mentorships']} mentorship records."
        ),
    )
    return redirect("dashboard:programs_manage")


@capability_required("manage_content")
def resources_manage(request):
    q = request.GET.get("q", "").strip()
    program = request.GET.get("program", "").strip()
    resources = ProgramResource.objects.select_related("program").order_by(
        "program__order", "order", "title"
    )
    if q:
        resources = resources.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
            | Q(external_url__icontains=q)
        )
    if program:
        resources = resources.filter(program_id=program)
    file_count = ProgramResource.objects.exclude(file="").count()
    link_count = ProgramResource.objects.exclude(external_url="").count()
    return render(request, "dashboard/resources_manage.html", {
        "resources": _paginate(request, resources, "resources_page", 18),
        "programs": Program.objects.order_by("order", "wing"),
        "q": q,
        "program": program,
        "totals": {
            "resources": ProgramResource.objects.count(),
            "files": file_count,
            "links": link_count,
            "drafts": ProgramResource.objects.filter(file="", external_url="").count(),
        },
    })


@capability_required("manage_content")
def resource_create(request):
    return _management_form(
        request,
        form_class=ProgramResourceForm,
        mode="Create",
        config={
            "label": "Program Resource",
            "description": "Attach a file or external link to a program page with a clear title and description.",
        },
        section="Resources",
        back_url="dashboard:resources_manage",
        success_url="dashboard:resource_edit",
        audit_action="resource.create",
    )


@capability_required("manage_content")
def resource_edit(request, pk):
    resource = get_object_or_404(ProgramResource, pk=pk)
    return _management_form(
        request,
        form_class=ProgramResourceForm,
        instance=resource,
        mode="Edit",
        config={
            "label": resource.title,
            "description": "Maintain the download/link details and the program this resource supports.",
        },
        section="Resources",
        back_url="dashboard:resources_manage",
        success_url="dashboard:resource_edit",
        audit_action="resource.update",
    )


@capability_required("manage_content")
@require_POST
def resource_delete(request, pk):
    resource = get_object_or_404(ProgramResource, pk=pk)
    title = resource.title
    resource.delete()
    log_action(request.user, "resource.delete", title)
    messages.success(request, f"{title} deleted.")
    return redirect("dashboard:resources_manage")


@capability_required("manage_content")
def speakers_manage(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    speakers = Speaker.objects.order_by("order", "name")
    if q:
        speakers = speakers.filter(Q(name__icontains=q) | Q(role__icontains=q))
    if status == "featured":
        speakers = speakers.filter(featured=True)
    elif status == "archive":
        speakers = speakers.filter(featured=False)
    return render(request, "dashboard/speakers_manage.html", {
        "speakers": _paginate(request, speakers, "speakers_page", 16),
        "q": q,
        "status": status,
        "totals": {
            "speakers": Speaker.objects.count(),
            "featured": Speaker.objects.filter(featured=True).count(),
            "photos": Speaker.objects.exclude(photo="").count(),
            "archive": Speaker.objects.filter(featured=False).count(),
        },
    })


@capability_required("manage_content")
def speaker_create(request):
    return _management_form(
        request,
        form_class=SpeakerForm,
        mode="Create",
        config={
            "label": "Speaker",
            "description": "Create a public speaker profile with role, photo, featured status, and ordering.",
        },
        section="Speakers",
        back_url="dashboard:speakers_manage",
        success_url="dashboard:speaker_edit",
        audit_action="speaker.create",
    )


@capability_required("manage_content")
def speaker_edit(request, pk):
    speaker = get_object_or_404(Speaker, pk=pk)
    return _management_form(
        request,
        form_class=SpeakerForm,
        instance=speaker,
        mode="Edit",
        config={
            "label": speaker.name,
            "description": "Refine the speaker profile and whether it appears in featured public sections.",
        },
        section="Speakers",
        back_url="dashboard:speakers_manage",
        success_url="dashboard:speaker_edit",
        audit_action="speaker.update",
    )


@capability_required("manage_content")
@require_POST
def speaker_delete(request, pk):
    speaker = get_object_or_404(Speaker, pk=pk)
    name = speaker.name
    speaker.delete()
    log_action(request.user, "speaker.delete", name)
    messages.success(request, f"{name} deleted.")
    return redirect("dashboard:speakers_manage")


@capability_required("manage_content")
def leadership_manage(request):
    q = request.GET.get("q", "").strip()
    position = request.GET.get("position", "").strip()
    team_members = TeamMember.objects.order_by("order", "position", "name")
    if q:
        team_members = team_members.filter(
            Q(name__icontains=q) | Q(title__icontains=q)
            | Q(credential__icontains=q) | Q(bio__icontains=q)
        )
    if position:
        team_members = team_members.filter(position=position)
    position_counts = dict(
        TeamMember.objects.values("position").annotate(c=Count("id")).values_list("position", "c")
    )
    return render(request, "dashboard/leadership_manage.html", {
        "team_members": _paginate(request, team_members, "team_page", 16),
        "q": q,
        "position": position,
        "position_choices": TeamMember.Position.choices,
        "totals": {
            "leaders": TeamMember.objects.count(),
            "directors": position_counts.get(TeamMember.Position.DIRECTOR, 0),
            "executive": (
                position_counts.get(TeamMember.Position.GLOBAL_LEAD, 0)
                + position_counts.get(TeamMember.Position.EXEC_DIRECTOR, 0)
            ),
            "photos": TeamMember.objects.exclude(photo="").count(),
        },
    })


@capability_required("manage_content")
def leadership_create(request):
    return _management_form(
        request,
        form_class=TeamMemberForm,
        mode="Create",
        config={
            "label": "Leadership Profile",
            "description": "Add a governance, executive, or director profile for the public leadership page.",
        },
        section="Leadership",
        back_url="dashboard:leadership_manage",
        success_url="dashboard:leadership_edit",
        audit_action="leadership.create",
    )


@capability_required("manage_content")
def leadership_edit(request, pk):
    member = get_object_or_404(TeamMember, pk=pk)
    return _management_form(
        request,
        form_class=TeamMemberForm,
        instance=member,
        mode="Edit",
        config={
            "label": member.name,
            "description": "Update biography, governance position, title, credential, photo, and ordering.",
        },
        section="Leadership",
        back_url="dashboard:leadership_manage",
        success_url="dashboard:leadership_edit",
        audit_action="leadership.update",
    )


@capability_required("manage_content")
@require_POST
def leadership_delete(request, pk):
    member = get_object_or_404(TeamMember, pk=pk)
    name = member.name
    member.delete()
    log_action(request.user, "leadership.delete", name)
    messages.success(request, f"{name} deleted.")
    return redirect("dashboard:leadership_manage")


CONTENT_REGISTRY = {
    "branding": {
        "model": SiteBranding, "form": SiteBrandingForm, "label": "Project profile",
        "description": "Control identity, logos, contact details, social links, and typography.",
        "add_label": "Project profile",
        "singleton": True,
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
        "stats": _paginate(request, SiteStat.objects.all(), "stats_page", 15),
        "testimonials": _paginate(
            request, Testimonial.objects.all(), "testimonials_page", 15),
        "gallery": _paginate(request, GalleryImage.objects.all(), "gallery_page", 15),
        "policies": _paginate(request, Policy.objects.all(), "policies_page", 15),
        "totals": {
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
    moved = _content_redirect(section, create=True)
    if moved:
        return moved
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
    moved = _content_redirect(section, pk=pk)
    if moved:
        return moved
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
@require_POST
def message_action(request, pk, action):
    msg = get_object_or_404(ContactMessage, pk=pk)
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
@require_POST
def partner_action(request, pk, action):
    enquiry = get_object_or_404(PartnerEnquiry, pk=pk)
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
    can_view_payments = request.user.can("view_donations")
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
            "labels": ["Registrations", "Applications", "Mentorships"] + (
                ["Paystack gifts"] if can_view_payments else []
            ),
            "values": [
                EventRegistration.objects.count(),
                Application.objects.count(),
                MentorshipEnrollment.objects.count(),
            ] + ([Donation.objects.count()] if can_view_payments else []),
        },
    }
    if can_view_payments:
        donation_status_counts = dict(
            Donation.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
        )
        chart_data["payments"] = [
            {"name": "Successful", "value": donation_status_counts.get(Donation.Status.SUCCESS, 0)},
            {"name": "Pending", "value": donation_status_counts.get(Donation.Status.PENDING, 0)},
            {"name": "Failed", "value": donation_status_counts.get(Donation.Status.FAILED, 0)},
        ]
    staff_members = User.objects.filter(role__in=[Role.ADMIN, Role.DIRECTOR, Role.MENTOR])
    payment_members = User.objects.none()
    if can_view_payments:
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
        )
    )
    if can_view_payments:
        engagement_rows = engagement_rows.annotate(
            gifts_count=Count("donations", distinct=True)
        ).order_by("-registrations_count", "-applications_count", "-gifts_count")
    else:
        engagement_rows = engagement_rows.order_by("-registrations_count", "-applications_count")
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
            "paystack_gifts": Donation.objects.count() if can_view_payments else None,
        },
        "can_manage_users": request.user.can("manage_users"),
        "can_view_payments": can_view_payments,
    })


@capability_required("manage_members")
def member_detail(request, pk):
    member = get_object_or_404(User, pk=pk)
    can_manage_users = request.user.can("manage_users")
    can_view_payments = request.user.can("view_donations")
    if request.method == "POST":
        form = MemberAdminForm(
            request.POST, request.FILES, instance=member, actor=request.user
        )
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
        form = MemberAdminForm(instance=member, actor=request.user)

    donations = Donation.objects.none()
    successful_donations = Donation.objects.none()
    chart_data = {}
    if can_view_payments:
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
        "can_manage_users": can_manage_users,
        "can_view_payments": can_view_payments,
        "stats": {
            "registrations": member.registrations.count(),
            "applications": member.applications.count(),
            "gifts": donations.count() if can_view_payments else None,
            "raised": (
                successful_donations.aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            ) if can_view_payments else None,
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
