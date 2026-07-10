"""Double-entry posting, automation, controls, and financial statements."""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (Budget, FiscalPeriod, Fund, JournalEntry, JournalLine,
                     LedgerAccount)


DEFAULT_ACCOUNTS = (
    ("1000", "Cash and bank", LedgerAccount.Type.ASSET),
    ("1100", "Paystack clearing", LedgerAccount.Type.ASSET),
    ("1200", "Accounts receivable", LedgerAccount.Type.ASSET),
    ("2000", "Accounts payable", LedgerAccount.Type.LIABILITY),
    ("3000", "Unrestricted net assets", LedgerAccount.Type.EQUITY),
    ("3100", "Restricted net assets", LedgerAccount.Type.EQUITY),
    ("4000", "Donation income", LedgerAccount.Type.INCOME),
    ("4100", "Grant and partnership income", LedgerAccount.Type.INCOME),
    ("5000", "Programme expenses", LedgerAccount.Type.EXPENSE),
    ("5100", "Event expenses", LedgerAccount.Type.EXPENSE),
    ("5200", "Operations expenses", LedgerAccount.Type.EXPENSE),
    ("5300", "Administration expenses", LedgerAccount.Type.EXPENSE),
    ("5400", "Bank and payment charges", LedgerAccount.Type.EXPENSE),
)


def ensure_accounting_defaults():
    accounts = {}
    for code, name, account_type in DEFAULT_ACCOUNTS:
        account, _ = LedgerAccount.objects.get_or_create(
            code=code, defaults={"name": name, "account_type": account_type}
        )
        accounts[code] = account
    fund, _ = Fund.objects.get_or_create(
        code="GENERAL", defaults={"name": "General Fund"}
    )
    return accounts, fund


def period_for(value, create=True):
    period = FiscalPeriod.objects.filter(
        starts_on__lte=value, ends_on__gte=value
    ).first()
    if period or not create:
        return period
    return FiscalPeriod.objects.create(
        name=f"FY {value.year}", starts_on=date(value.year, 1, 1),
        ends_on=date(value.year, 12, 31),
    )


@transaction.atomic
def post_journal(journal, actor):
    journal = JournalEntry.objects.select_for_update().get(pk=journal.pk)
    if journal.status != JournalEntry.Status.DRAFT:
        raise ValidationError("Only draft journals can be posted.")
    period = journal.fiscal_period or period_for(journal.entry_date)
    if period.status == FiscalPeriod.Status.CLOSED:
        raise ValidationError("This fiscal period is closed.")
    if not journal.lines.exists() or not journal.is_balanced:
        raise ValidationError("Journal debits and credits must balance above zero.")
    journal.fiscal_period = period
    journal.status = JournalEntry.Status.POSTED
    journal.approved_by = actor
    journal.posted_at = timezone.now()
    journal.save(update_fields=["fiscal_period", "status", "approved_by", "posted_at"])
    return journal


@transaction.atomic
def reverse_journal(journal, actor, reversal_date=None):
    journal = JournalEntry.objects.select_for_update().get(pk=journal.pk)
    if journal.status != JournalEntry.Status.POSTED:
        raise ValidationError("Only posted journals can be reversed.")
    if hasattr(journal, "reversal"):
        raise ValidationError("This journal already has a reversal.")
    reversal = JournalEntry.objects.create(
        entry_date=reversal_date or timezone.localdate(),
        description=f"Reversal: {journal.description}", reference=journal.number,
        fund=journal.fund, reversal_of=journal, created_by=actor,
    )
    for line in journal.lines.all():
        JournalLine.objects.create(
            journal=reversal, account=line.account,
            description=f"Reversal: {line.description}",
            debit=line.credit, credit=line.debit,
        )
    post_journal(reversal, actor)
    journal.status = JournalEntry.Status.REVERSED
    journal.save(update_fields=["status"])
    return reversal


@transaction.atomic
def create_source_journal(*, source_type, source_id, entry_date, description,
                          debit_code, credit_code, amount, actor=None,
                          reference="", fund=None):
    existing = JournalEntry.objects.filter(
        source_type=source_type, source_id=source_id
    ).first()
    if existing:
        return existing
    accounts, general_fund = ensure_accounting_defaults()
    journal = JournalEntry.objects.create(
        entry_date=entry_date, description=description, reference=reference,
        source_type=source_type, source_id=source_id,
        fund=fund or general_fund, created_by=actor,
    )
    amount = Decimal(str(amount))
    JournalLine.objects.create(
        journal=journal, account=accounts[debit_code], debit=amount,
        description=description,
    )
    JournalLine.objects.create(
        journal=journal, account=accounts[credit_code], credit=amount,
        description=description,
    )
    return post_journal(journal, actor)


def post_donation(donation, actor=None):
    return create_source_journal(
        source_type="donation", source_id=donation.pk,
        entry_date=donation.created_at.date(),
        description=f"Donation: {donation.donor_name or 'Anonymous'}",
        debit_code="1100", credit_code="4000", amount=donation.amount,
        actor=actor, reference=donation.reference,
    )


EXPENSE_ACCOUNT = {
    "PROGRAMS": "5000", "MENTORSHIP": "5000", "OUTREACH": "5000",
    "EVENTS": "5100", "OPERATIONS": "5200", "MEDIA": "5200",
    "TECHNOLOGY": "5200", "ADMIN": "5300", "OTHER": "5200",
}


def post_expense(expense, actor=None):
    return create_source_journal(
        source_type="expense", source_id=expense.pk,
        entry_date=expense.expense_date, description=f"Expense: {expense.title}",
        debit_code=EXPENSE_ACCOUNT.get(expense.category, "5200"),
        credit_code="1000" if expense.status == expense.Status.PAID else "2000",
        amount=expense.amount, actor=actor, reference=expense.reference,
    )


def financial_statements(start, end, fund=None, budget=None):
    lines = JournalLine.objects.filter(
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__gte=start, journal__entry_date__lte=end,
    ).select_related("account")
    if fund:
        lines = lines.filter(journal__fund=fund)
    rows = (
        lines.values("account_id", "account__code", "account__name", "account__account_type")
        .annotate(debits=Sum("debit"), credits=Sum("credit"))
        .order_by("account__code")
    )
    trial, income_rows, expense_rows, asset_rows, liability_rows, equity_rows = [], [], [], [], [], []
    for row in rows:
        debit = row["debits"] or Decimal("0.00")
        credit = row["credits"] or Decimal("0.00")
        raw = debit - credit
        display = raw if row["account__account_type"] in {
            LedgerAccount.Type.ASSET, LedgerAccount.Type.EXPENSE
        } else -raw
        item = {"code": row["account__code"], "name": row["account__name"],
                "type": row["account__account_type"], "debit": debit,
                "credit": credit, "balance": display}
        trial.append(item)
        target = {
            LedgerAccount.Type.INCOME: income_rows,
            LedgerAccount.Type.EXPENSE: expense_rows,
            LedgerAccount.Type.ASSET: asset_rows,
            LedgerAccount.Type.LIABILITY: liability_rows,
            LedgerAccount.Type.EQUITY: equity_rows,
        }[row["account__account_type"]]
        target.append(item)
    income = sum((r["balance"] for r in income_rows), Decimal("0.00"))
    expenses = sum((r["balance"] for r in expense_rows), Decimal("0.00"))
    budget_rows = []
    if budget:
        actual_lookup = {r["code"]: r["balance"] for r in income_rows + expense_rows}
        for line in budget.lines.select_related("account"):
            actual = actual_lookup.get(line.account.code, Decimal("0.00"))
            variance = actual - line.amount if line.account.account_type == LedgerAccount.Type.INCOME else line.amount - actual
            budget_rows.append({"account": line.account, "budget": line.amount,
                                "actual": actual, "variance": variance,
                                "variance_pct": round(variance / line.amount * 100, 1) if line.amount else 0})
    return {
        "trial_balance": trial, "income_rows": income_rows,
        "expense_rows": expense_rows, "asset_rows": asset_rows,
        "liability_rows": liability_rows, "equity_rows": equity_rows,
        "income": income, "expenses": expenses, "surplus": income - expenses,
        "assets": sum((r["balance"] for r in asset_rows), Decimal("0.00")),
        "liabilities": sum((r["balance"] for r in liability_rows), Decimal("0.00")),
        "net_assets": sum((r["balance"] for r in equity_rows), Decimal("0.00")) + income - expenses,
        "budget_rows": budget_rows,
        "trial_debits": sum((r["debit"] for r in trial), Decimal("0.00")),
        "trial_credits": sum((r["credit"] for r in trial), Decimal("0.00")),
    }
