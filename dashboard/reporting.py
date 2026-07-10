"""Shared finance/reporting calculations kept separate from HTTP views."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import CashAccount, CashMovement


def cash_account_balance_map(accounts=None):
    accounts = accounts if accounts is not None else CashAccount.objects.all()
    balances = {
        account.pk: account.opening_balance or Decimal("0.00")
        for account in accounts
    }
    source_rows = (
        CashMovement.objects
        .filter(status=CashMovement.Status.POSTED, account_id__in=balances)
        .values("account_id", "direction")
        .annotate(total=Sum("amount"))
    )
    for row in source_rows:
        amount = row["total"] or Decimal("0.00")
        if row["direction"] == CashMovement.Direction.IN:
            balances[row["account_id"]] += amount
        else:
            balances[row["account_id"]] -= amount
    transfer_rows = (
        CashMovement.objects
        .filter(
            status=CashMovement.Status.POSTED,
            direction=CashMovement.Direction.TRANSFER,
            transfer_account_id__in=balances,
        )
        .values("transfer_account_id")
        .annotate(total=Sum("amount"))
    )
    for row in transfer_rows:
        balances[row["transfer_account_id"]] += row["total"] or Decimal("0.00")
    return balances


def cash_account_rows(accounts):
    account_list = list(accounts)
    balances = cash_account_balance_map(account_list)
    return [
        {
            "account": account,
            "balance": balances.get(account.pk, Decimal("0.00")),
            "variance": (
                balances.get(account.pk, Decimal("0.00"))
                - (account.statement_balance or Decimal("0.00"))
            ),
        }
        for account in account_list
    ]


def report_permissions(user):
    return {
        "executive": user.can("view_org_analytics"),
        "finance": user.can("view_donations"),
        "events": user.can("view_org_analytics") or user.can("manage_events"),
        "people": (
            user.can("view_org_analytics") or user.can("manage_members")
            or user.can("manage_applications") or user.can("manage_mentorship")
        ),
        "content": (
            user.can("view_org_analytics") or user.can("manage_content")
            or user.can("manage_media") or user.can("manage_speakers")
            or user.can("manage_testimonials")
        ),
        "engagement": (
            user.can("view_org_analytics") or user.can("manage_contact")
            or user.can("view_partners") or user.can("manage_partners")
            or user.can("manage_applications")
        ),
    }


def can_view_reports(user):
    return any(report_permissions(user).values())


def report_period(request):
    today = timezone.localdate()
    start = parse_date(request.GET.get("start", "")) or (today - timedelta(days=365))
    end = parse_date(request.GET.get("end", "")) or today
    if start > end:
        start, end = end, start
    return {"start": start, "end": end, "days": (end - start).days + 1}


def month_key(value):
    return value.strftime("%Y-%m") if value else ""


def month_label(key):
    year, month = map(int, key.split("-"))
    return timezone.datetime(year, month, 1).strftime("%b %Y")
