"""Dashboard-specific models: finance records and admin audit trail."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from accounts.models import Role


class Expense(models.Model):
    """A finance expense/expenditure record managed from the dashboard."""

    class Category(models.TextChoices):
        PROGRAMS = "PROGRAMS", "Programs"
        EVENTS = "EVENTS", "Events"
        MENTORSHIP = "MENTORSHIP", "Mentorship"
        OUTREACH = "OUTREACH", "Humanitarian Outreach"
        OPERATIONS = "OPERATIONS", "Operations"
        MEDIA = "MEDIA", "Media / Communications"
        TECHNOLOGY = "TECHNOLOGY", "Technology"
        ADMIN = "ADMIN", "Administration"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    title = models.CharField(max_length=180)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OPERATIONS,
        db_index=True,
    )
    payee = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="GHS")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    expense_date = models.DateField(default=timezone.localdate, db_index=True)
    payment_method = models.CharField(max_length=80, blank=True)
    reference = models.CharField(max_length=80, blank=True)
    receipt = models.FileField(upload_to="expenses/", blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="recorded_expenses",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.currency} {self.amount:.2f}"

    @property
    def is_posted(self):
        return self.status in {self.Status.APPROVED, self.Status.PAID}


class CashAccount(models.Model):
    """Cash, bank, mobile money, and gateway accounts tracked by finance."""

    class AccountType(models.TextChoices):
        CASH = "CASH", "Cash on hand"
        BANK = "BANK", "Bank account"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile money wallet"
        PAYMENT_GATEWAY = "PAYMENT_GATEWAY", "Payment gateway"
        SAVINGS = "SAVINGS", "Savings / reserve"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=160)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.BANK,
        db_index=True,
    )
    institution_name = models.CharField(max_length=160, blank=True)
    account_number = models.CharField(max_length=80, blank=True)
    branch = models.CharField(max_length=120, blank=True)
    currency = models.CharField(max_length=8, default="GHS")
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opening_balance_date = models.DateField(default=timezone.localdate)
    statement_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Most recent bank or cash-count statement balance.",
    )
    last_reconciled_on = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    is_primary = models.BooleanField(default=False)
    accepts_donations = models.BooleanField(default=True)
    pays_expenses = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    ledger_account = models.ForeignKey(
        "LedgerAccount", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cash_accounts",
        help_text="Asset account used for double-entry posting.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_cash_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "account_type", "name"]

    def __str__(self):
        return self.name

    @property
    def masked_account_number(self):
        if not self.account_number:
            return "Not supplied"
        suffix = self.account_number[-4:]
        return f"**** {suffix}" if len(self.account_number) > 4 else self.account_number


class CashMovement(models.Model):
    """A cash/bank movement used for balance, transfer, and reconciliation tracking."""

    class Direction(models.TextChoices):
        IN = "IN", "Money in"
        OUT = "OUT", "Money out"
        TRANSFER = "TRANSFER", "Transfer"

    class Category(models.TextChoices):
        DONATION_CLEARING = "DONATION_CLEARING", "Donation clearing"
        EXPENSE_PAYMENT = "EXPENSE_PAYMENT", "Expense payment"
        CASH_DEPOSIT = "CASH_DEPOSIT", "Cash deposit"
        CASH_WITHDRAWAL = "CASH_WITHDRAWAL", "Cash withdrawal"
        BANK_CHARGE = "BANK_CHARGE", "Bank charge"
        TRANSFER = "TRANSFER", "Internal transfer"
        OPENING_ADJUSTMENT = "OPENING_ADJUSTMENT", "Opening adjustment"
        RECONCILIATION = "RECONCILIATION", "Reconciliation adjustment"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        VOID = "VOID", "Void"

    account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, related_name="movements"
    )
    transfer_account = models.ForeignKey(
        CashAccount, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incoming_transfers",
        help_text="Destination account for internal transfers.",
    )
    direction = models.CharField(
        max_length=10, choices=Direction.choices, default=Direction.IN, db_index=True
    )
    category = models.CharField(
        max_length=24, choices=Category.choices, default=Category.OTHER, db_index=True
    )
    title = models.CharField(max_length=180)
    counterparty = models.CharField(max_length=180, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="GHS")
    movement_date = models.DateField(default=timezone.localdate, db_index=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    reference = models.CharField(max_length=100, blank=True)
    linked_donation = models.ForeignKey(
        "donations.Donation", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cash_movements",
    )
    linked_expense = models.ForeignKey(
        Expense, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cash_movements",
    )
    memo = models.TextField(blank=True)
    attachment = models.FileField(upload_to="cash-movements/", blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="recorded_cash_movements",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_cash_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-movement_date", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.currency} {self.amount:.2f}"

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})
        if self.direction == self.Direction.TRANSFER:
            if not self.transfer_account:
                raise ValidationError({"transfer_account": "Select the destination account."})
            if self.account_id and self.transfer_account_id == self.account_id:
                raise ValidationError({"transfer_account": "Choose a different destination account."})
        elif self.transfer_account_id:
            raise ValidationError({"transfer_account": "Destination account is only used for transfers."})
        if self.account_id and self.currency and self.currency != self.account.currency:
            raise ValidationError({"currency": "Currency must match the source account."})
        if (
            self.transfer_account_id and self.account_id
            and self.transfer_account.currency != self.account.currency
        ):
            raise ValidationError({"transfer_account": "Transfers must use accounts with the same currency."})

    @property
    def is_posted(self):
        return self.status == self.Status.POSTED


class Fund(models.Model):
    class Type(models.TextChoices):
        UNRESTRICTED = "UNRESTRICTED", "Unrestricted"
        TEMP_RESTRICTED = "TEMP_RESTRICTED", "Temporarily restricted"
        PERM_RESTRICTED = "PERM_RESTRICTED", "Permanently restricted"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    fund_type = models.CharField(max_length=20, choices=Type.choices, default=Type.UNRESTRICTED)
    donor = models.CharField(max_length=160, blank=True)
    restriction = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"


class FiscalPeriod(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=80, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="closed_fiscal_periods")

    class Meta:
        ordering = ["-starts_on"]

    def clean(self):
        if self.starts_on and self.ends_on and self.starts_on > self.ends_on:
            raise ValidationError({"ends_on": "Period end must be on or after its start."})
        overlap = FiscalPeriod.objects.exclude(pk=self.pk).filter(
            starts_on__lte=self.ends_on, ends_on__gte=self.starts_on
        ) if self.starts_on and self.ends_on else FiscalPeriod.objects.none()
        if overlap.exists():
            raise ValidationError("Fiscal periods cannot overlap.")

    def __str__(self):
        return self.name


class LedgerAccount(models.Model):
    class Type(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Net assets / equity"
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    account_type = models.CharField(max_length=12, choices=Type.choices, db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    allow_posting = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    @property
    def normal_balance(self):
        return "DEBIT" if self.account_type in {self.Type.ASSET, self.Type.EXPENSE} else "CREDIT"


class JournalEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"

    number = models.CharField(max_length=30, unique=True, blank=True)
    entry_date = models.DateField(default=timezone.localdate, db_index=True)
    description = models.CharField(max_length=240)
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    fiscal_period = models.ForeignKey(FiscalPeriod, null=True, blank=True, on_delete=models.PROTECT, related_name="journals")
    fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.PROTECT, related_name="journals")
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    reversal_of = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_journals")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_journals")
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["source_type", "source_id"], condition=models.Q(source_type__gt="", source_id__isnull=False), name="unique_accounting_source")]

    def save(self, *args, **kwargs):
        if not self.number:
            prefix = f"JE-{self.entry_date:%Y%m}-"
            last = JournalEntry.objects.filter(number__startswith=prefix).order_by("number").last()
            sequence = int(last.number.rsplit("-", 1)[-1]) + 1 if last else 1
            self.number = f"{prefix}{sequence:04d}"
        super().save(*args, **kwargs)

    @property
    def total_debits(self):
        return self.lines.aggregate(total=models.Sum("debit"))["total"] or 0

    @property
    def total_credits(self):
        return self.lines.aggregate(total=models.Sum("credit"))["total"] or 0

    @property
    def is_balanced(self):
        return self.total_debits == self.total_credits and self.total_debits > 0

    def __str__(self):
        return f"{self.number} · {self.description}"


class JournalLine(models.Model):
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name="journal_lines")
    description = models.CharField(max_length=200, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["pk"]

    def clean(self):
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Debit and credit values cannot be negative.")
        if bool(self.debit) == bool(self.credit):
            raise ValidationError("Enter either a debit or credit amount, not both.")
        if self.account_id and not self.account.allow_posting:
            raise ValidationError({"account": "This control account does not allow direct posting."})

    def __str__(self):
        return f"{self.account} · Dr {self.debit:.2f} Cr {self.credit:.2f}"


class Budget(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        LOCKED = "LOCKED", "Locked"

    name = models.CharField(max_length=160)
    fiscal_period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT, related_name="budgets")
    fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.PROTECT, related_name="budgets")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_budgets")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_budgets")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fiscal_period__starts_on", "name"]
        constraints = [models.UniqueConstraint(fields=["name", "fiscal_period", "fund"], name="unique_budget_scope")]

    def __str__(self):
        return self.name

    @property
    def total_amount(self):
        return self.lines.aggregate(total=models.Sum("amount"))["total"] or 0


class BudgetLine(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name="budget_lines")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["account__code"]
        constraints = [models.UniqueConstraint(fields=["budget", "account"], name="unique_budget_account")]

    def clean(self):
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Budget amount cannot be negative."})


class BankReconciliation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECONCILED = "RECONCILED", "Reconciled"

    account = models.ForeignKey(CashAccount, on_delete=models.PROTECT, related_name="reconciliations")
    statement_date = models.DateField(default=timezone.localdate)
    statement_balance = models.DecimalField(max_digits=14, decimal_places=2)
    book_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    outstanding_deposits = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    outstanding_payments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    adjustments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="prepared_reconciliations")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_reconciliations")
    reconciled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-statement_date"]
        constraints = [models.UniqueConstraint(fields=["account", "statement_date"], name="unique_account_statement_date")]

    @property
    def adjusted_statement_balance(self):
        return self.statement_balance + self.outstanding_deposits - self.outstanding_payments + self.adjustments

    @property
    def difference(self):
        return self.book_balance - self.adjusted_statement_balance

    def __str__(self):
        return f"{self.account} · {self.statement_date}"


class AuditLog(models.Model):
    """A record of a significant admin action for accountability."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=200, blank=True)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.actor or "system"
        return f"{who}: {self.action} — {self.target}"


def log_action(actor, action, target="", detail=""):
    """Convenience helper used by dashboard views to record admin actions."""
    try:
        AuditLog.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            action=action, target=str(target)[:200], detail=str(detail)[:300],
        )
    except Exception:  # pragma: no cover - audit must never break a request
        pass


class IntegrationSettings(models.Model):
    """Singleton credentials and defaults for communications and payments."""
    class SmsProvider(models.TextChoices):
        ARKESEL = "ARKESEL", "Arkesel"
        HUBTEL = "HUBTEL", "Hubtel"

    sms_enabled = models.BooleanField(default=False)
    sms_provider = models.CharField(
        max_length=12, choices=SmsProvider.choices, default=SmsProvider.ARKESEL
    )
    sms_sender_id = models.CharField(max_length=11, blank=True, default="OIF")
    arkesel_api_key = models.CharField(max_length=255, blank=True)
    arkesel_base_url = models.URLField(
        default="https://sms.arkesel.com/api/v2/sms/send", blank=True
    )
    hubtel_client_id = models.CharField(max_length=255, blank=True)
    hubtel_client_secret = models.CharField(max_length=255, blank=True)
    hubtel_base_url = models.URLField(
        default="https://smsc.hubtel.com/v1/messages/send", blank=True
    )
    whatsapp_enabled = models.BooleanField(default=False)
    whatsapp_access_token = models.CharField(max_length=255, blank=True)
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True)
    whatsapp_business_number = models.CharField(max_length=32, blank=True)
    email_enabled = models.BooleanField(default=True)
    email_from_name = models.CharField(max_length=120, blank=True, default="OIF")
    paystack_use_cms_configuration = models.BooleanField(
        default=False,
        help_text="Use the Paystack values below instead of environment variables.",
    )
    paystack_enabled = models.BooleanField(default=False)
    paystack_public_key = models.CharField(max_length=255, blank=True)
    paystack_secret_key = models.CharField(max_length=255, blank=True)
    paystack_webhook_secret = models.CharField(max_length=255, blank=True)
    paystack_demo_mode = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="integration_updates"
    )

    class Meta:
        verbose_name_plural = "Integration settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Messaging and payment integrations"


class MessageTemplate(models.Model):
    name = models.CharField(max_length=160, unique=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="message_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MessageCampaign(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        ALL = "ALL", "Email, SMS and WhatsApp"

    class Audience(models.TextChoices):
        ALL_MEMBERS = "ALL_MEMBERS", "All active members"
        MARKETING = "MARKETING", "Marketing opt-ins"
        ROLE = "ROLE", "Members in selected role"
        EVENT = "EVENT", "Event registrants"
        NEWSLETTER = "NEWSLETTER", "Newsletter subscribers"
        CUSTOM = "CUSTOM", "Custom recipients"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PROCESSING = "PROCESSING", "Processing"
        SENT = "SENT", "Sent"
        PARTIAL = "PARTIAL", "Partially sent"
        FAILED = "FAILED", "Failed"

    title = models.CharField(max_length=180)
    channel = models.CharField(max_length=12, choices=Channel.choices)
    audience = models.CharField(max_length=20, choices=Audience.choices)
    role = models.CharField(max_length=20, choices=Role.choices, blank=True)
    event = models.ForeignKey("pages.Event", null=True, blank=True, on_delete=models.SET_NULL)
    custom_recipients = models.TextField(blank=True, help_text="One email address or phone number per line.")
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(help_text="Use {name}, {first_name}, {email}, {phone}, and {org_name} placeholders.")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="message_campaigns")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MessageDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    campaign = models.ForeignKey(MessageCampaign, on_delete=models.CASCADE, related_name="deliveries")
    channel = models.CharField(max_length=12, choices=MessageCampaign.Channel.choices)
    recipient = models.CharField(max_length=254)
    recipient_name = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider = models.CharField(max_length=40, blank=True)
    provider_reference = models.CharField(max_length=160, blank=True)
    error = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["campaign", "status"])]

    def __str__(self):
        return f"{self.channel} to {self.recipient}"
