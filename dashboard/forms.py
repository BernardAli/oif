from django import forms
from django.forms import inlineformset_factory

from accounts.models import User
from engagement.models import MentorshipEnrollment
from pages.models import (Event, Program, ProgramResource, SiteBranding,
                          SiteStat, Speaker, TeamMember, Testimonial,
                          GalleryImage, Policy)
from .models import (CashAccount, CashMovement, Expense, IntegrationSettings,
                     MessageCampaign, MessageTemplate, BankReconciliation,
                     Budget, BudgetLine, FiscalPeriod, Fund, JournalEntry,
                     JournalLine, LedgerAccount)


class SecretPreservingForm(forms.ModelForm):
    """Do not erase stored credentials when password inputs are left blank."""
    secret_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.secret_fields:
            self.fields[name].required = False
            self.fields[name].widget = forms.PasswordInput(
                attrs={"class": "form-input", "autocomplete": "new-password"},
                render_value=False,
            )
            if self.instance.pk and getattr(self.instance, name):
                self.fields[name].help_text = "Configured. Leave blank to keep the current value."

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            for name in self.secret_fields:
                if not cleaned.get(name):
                    cleaned[name] = getattr(self.instance, name)
        return cleaned


class IntegrationSettingsForm(SecretPreservingForm):
    secret_fields = (
        "arkesel_api_key", "hubtel_client_id", "hubtel_client_secret",
        "whatsapp_access_token", "paystack_public_key", "paystack_secret_key",
        "paystack_webhook_secret",
    )

    class Meta:
        model = IntegrationSettings
        exclude = ("updated_by",)
        widgets = {
            "sms_provider": forms.Select(attrs={"class": "form-input"}),
            "sms_sender_id": forms.TextInput(attrs={"class": "form-input"}),
            "arkesel_base_url": forms.URLInput(attrs={"class": "form-input"}),
            "hubtel_base_url": forms.URLInput(attrs={"class": "form-input"}),
            "whatsapp_phone_number_id": forms.TextInput(attrs={"class": "form-input"}),
            "whatsapp_business_number": forms.TextInput(attrs={"class": "form-input"}),
            "email_from_name": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean_sms_sender_id(self):
        sender = self.cleaned_data["sms_sender_id"].strip()
        if len(sender) > 11:
            raise forms.ValidationError("SMS sender IDs may contain at most 11 characters.")
        return sender


class MessageCampaignForm(forms.ModelForm):
    template = forms.ModelChoiceField(
        queryset=MessageTemplate.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs={"class": "form-input"}),
        help_text="Optional starting point; campaign text below remains editable.",
    )

    class Meta:
        model = MessageCampaign
        fields = ("title", "channel", "audience", "role", "event", "template",
                  "custom_recipients", "subject", "body")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "channel": forms.Select(attrs={"class": "form-input"}),
            "audience": forms.Select(attrs={"class": "form-input"}),
            "role": forms.Select(attrs={"class": "form-input"}),
            "event": forms.Select(attrs={"class": "form-input"}),
            "custom_recipients": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "subject": forms.TextInput(attrs={"class": "form-input"}),
            "body": forms.Textarea(attrs={"class": "form-input", "rows": 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"].required = False

    def clean(self):
        cleaned = super().clean()
        template = cleaned.get("template")
        if template:
            cleaned["subject"] = cleaned.get("subject") or template.subject
            cleaned["body"] = cleaned.get("body") or template.body
        if not cleaned.get("body", "").strip():
            self.add_error("body", "Enter message content or select a template.")
        audience = cleaned.get("audience")
        if audience == MessageCampaign.Audience.ROLE and not cleaned.get("role"):
            self.add_error("role", "Select a role for this audience.")
        if audience == MessageCampaign.Audience.EVENT and not cleaned.get("event"):
            self.add_error("event", "Select an event for this audience.")
        if audience == MessageCampaign.Audience.CUSTOM and not cleaned.get("custom_recipients", "").strip():
            self.add_error("custom_recipients", "Enter at least one recipient.")
        if cleaned.get("channel") in (MessageCampaign.Channel.EMAIL, MessageCampaign.Channel.ALL) and not cleaned.get("subject"):
            self.add_error("subject", "Email campaigns require a subject.")
        return cleaned

    def save(self, commit=True):
        campaign = super().save(commit=False)
        template = self.cleaned_data.get("template")
        if template:
            if not campaign.subject:
                campaign.subject = template.subject
            if not campaign.body:
                campaign.body = template.body
        if commit:
            campaign.save()
        return campaign


class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ("name", "subject", "body", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "subject": forms.TextInput(attrs={"class": "form-input"}),
            "body": forms.Textarea(attrs={"class": "form-input", "rows": 10}),
        }


class LedgerAccountForm(forms.ModelForm):
    class Meta:
        model = LedgerAccount
        fields = ("code", "name", "account_type", "parent", "description",
                  "is_active", "allow_posting")
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "account_type": forms.Select(attrs={"class": "form-input"}),
            "parent": forms.Select(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }


class FundForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ("code", "name", "fund_type", "donor", "restriction", "is_active")
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "fund_type": forms.Select(attrs={"class": "form-input"}),
            "donor": forms.TextInput(attrs={"class": "form-input"}),
            "restriction": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }


class FiscalPeriodForm(forms.ModelForm):
    class Meta:
        model = FiscalPeriod
        fields = ("name", "starts_on", "ends_on")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "starts_on": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "ends_on": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ("entry_date", "description", "reference", "fiscal_period", "fund")
        widgets = {
            "entry_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "description": forms.TextInput(attrs={"class": "form-input"}),
            "reference": forms.TextInput(attrs={"class": "form-input"}),
            "fiscal_period": forms.Select(attrs={"class": "form-input"}),
            "fund": forms.Select(attrs={"class": "form-input"}),
        }


class JournalLineForm(forms.ModelForm):
    class Meta:
        model = JournalLine
        fields = ("account", "description", "debit", "credit")
        widgets = {
            "account": forms.Select(attrs={"class": "form-input"}),
            "description": forms.TextInput(attrs={"class": "form-input"}),
            "debit": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": 0}),
            "credit": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": 0}),
        }


JournalLineFormSet = inlineformset_factory(
    JournalEntry, JournalLine, form=JournalLineForm, extra=4,
    min_num=2, validate_min=True, can_delete=True,
)


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ("name", "fiscal_period", "fund", "notes")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "fiscal_period": forms.Select(attrs={"class": "form-input"}),
            "fund": forms.Select(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ("account", "amount", "notes")
        widgets = {
            "account": forms.Select(attrs={"class": "form-input"}),
            "amount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": 0}),
            "notes": forms.TextInput(attrs={"class": "form-input"}),
        }


BudgetLineFormSet = inlineformset_factory(
    Budget, BudgetLine, form=BudgetLineForm, extra=8,
    min_num=1, validate_min=True, can_delete=True,
)


class BankReconciliationForm(forms.ModelForm):
    class Meta:
        model = BankReconciliation
        fields = ("account", "statement_date", "statement_balance", "book_balance",
                  "outstanding_deposits", "outstanding_payments", "adjustments", "notes")
        widgets = {
            "account": forms.Select(attrs={"class": "form-input"}),
            "statement_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "statement_balance": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "book_balance": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "outstanding_deposits": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "outstanding_payments": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "adjustments": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }


class EventForm(forms.ModelForm):
    starts_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S%z"],
        widget=forms.DateTimeInput(
            attrs={"class": "form-input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Event
        fields = (
            "title", "kind", "program", "theme", "summary", "description",
            "audience", "outcomes", "agenda", "speakers", "preparation",
            "accessibility", "flyer", "starts_at", "location", "venue_address",
            "online_url", "is_virtual", "capacity", "registration_note",
            "contact_email",
            "registration_open", "is_published",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "kind": forms.Select(attrs={"class": "form-input"}),
            "program": forms.Select(attrs={"class": "form-input"}),
            "theme": forms.TextInput(attrs={"class": "form-input"}),
            "summary": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "audience": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "outcomes": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "agenda": forms.Textarea(attrs={"class": "form-input", "rows": 6}),
            "speakers": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "preparation": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "accessibility": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "flyer": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
            "venue_address": forms.TextInput(attrs={"class": "form-input"}),
            "online_url": forms.URLInput(attrs={"class": "form-input"}),
            "capacity": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
            "registration_note": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "contact_email": forms.EmailInput(attrs={"class": "form-input"}),
        }
        help_texts = {
            "capacity": "Use 0 for unlimited seats.",
            "is_published": "Published events can appear on the public site.",
            "registration_open": "Controls whether members can register.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("is_virtual", "registration_open", "is_published"):
            self.fields[field_name].widget.attrs["class"] = "check-input"


class MemberAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "role", "is_active", "is_staff", "title", "location", "avatar",
            "is_public_profile",
        )
        widgets = {
            "role": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if actor is not None and not actor.can("manage_users"):
            self.fields.pop("role", None)
            self.fields.pop("is_staff", None)
        for field_name in ("is_active", "is_staff", "is_public_profile"):
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["class"] = "check-input"


class MentorshipEnrollmentForm(forms.ModelForm):
    class Meta:
        model = MentorshipEnrollment
        fields = (
            "mentee", "mentor", "program", "cohort", "phase",
            "sessions_completed", "sessions_total",
        )
        widgets = {
            "mentee": forms.Select(attrs={"class": "form-input"}),
            "mentor": forms.Select(attrs={"class": "form-input"}),
            "program": forms.Select(attrs={"class": "form-input"}),
            "cohort": forms.TextInput(attrs={"class": "form-input"}),
            "phase": forms.Select(attrs={"class": "form-input"}),
            "sessions_completed": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
            "sessions_total": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
        }


class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )

    class Meta:
        model = Expense
        fields = (
            "title", "category", "payee", "description", "amount", "currency",
            "status", "expense_date", "payment_method", "reference", "receipt",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "category": forms.Select(attrs={"class": "form-input"}),
            "payee": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "amount": forms.NumberInput(attrs={
                "class": "form-input", "step": "0.01", "min": "0.01",
            }),
            "currency": forms.TextInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "payment_method": forms.TextInput(attrs={"class": "form-input"}),
            "reference": forms.TextInput(attrs={"class": "form-input"}),
            "receipt": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }
        help_texts = {
            "status": "Approved and paid expenses are included in recognized expenditure.",
            "receipt": "Upload an invoice, receipt, or supporting document when available.",
        }


class CashAccountForm(forms.ModelForm):
    opening_balance_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )
    last_reconciled_on = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )

    class Meta:
        model = CashAccount
        fields = (
            "name", "account_type", "institution_name", "account_number",
            "branch", "currency", "opening_balance", "opening_balance_date",
            "statement_balance", "last_reconciled_on", "status", "is_primary",
            "accepts_donations", "pays_expenses", "ledger_account", "notes",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "account_type": forms.Select(attrs={"class": "form-input"}),
            "institution_name": forms.TextInput(attrs={"class": "form-input"}),
            "account_number": forms.TextInput(attrs={"class": "form-input"}),
            "branch": forms.TextInput(attrs={"class": "form-input"}),
            "currency": forms.TextInput(attrs={"class": "form-input"}),
            "opening_balance": forms.NumberInput(attrs={
                "class": "form-input", "step": "0.01",
            }),
            "statement_balance": forms.NumberInput(attrs={
                "class": "form-input", "step": "0.01",
            }),
            "status": forms.Select(attrs={"class": "form-input"}),
            "ledger_account": forms.Select(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
        }
        help_texts = {
            "opening_balance": "Starting book balance before tracked cash movements.",
            "statement_balance": "Latest bank statement or physical cash-count balance.",
            "last_reconciled_on": "Date this account was last checked against a statement or cash count.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("is_primary", "accepts_donations", "pays_expenses"):
            self.fields[field_name].widget.attrs["class"] = "check-input"


class CashMovementForm(forms.ModelForm):
    movement_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )

    class Meta:
        model = CashMovement
        fields = (
            "account", "transfer_account", "direction", "category", "title",
            "counterparty", "amount", "currency", "movement_date", "status",
            "reference", "linked_donation", "linked_expense", "memo",
            "attachment",
        )
        widgets = {
            "account": forms.Select(attrs={"class": "form-input"}),
            "transfer_account": forms.Select(attrs={"class": "form-input"}),
            "direction": forms.Select(attrs={"class": "form-input"}),
            "category": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "counterparty": forms.TextInput(attrs={"class": "form-input"}),
            "amount": forms.NumberInput(attrs={
                "class": "form-input", "step": "0.01", "min": "0.01",
            }),
            "currency": forms.TextInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "reference": forms.TextInput(attrs={"class": "form-input"}),
            "linked_donation": forms.Select(attrs={"class": "form-input"}),
            "linked_expense": forms.Select(attrs={"class": "form-input"}),
            "memo": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }
        help_texts = {
            "transfer_account": "Required only when direction is Transfer.",
            "status": "Only posted movements affect cash and bank balances.",
            "linked_donation": "Optional: connect this movement to a donation clearing entry.",
            "linked_expense": "Optional: connect this movement to a paid expense.",
        }


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ("wing", "tagline", "headline", "description", "image",
                  "accent", "order", "is_active")
        widgets = {
            "wing": forms.Select(attrs={"class": "form-input"}),
            "tagline": forms.TextInput(attrs={"class": "form-input"}),
            "headline": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "image": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "accent": forms.TextInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].widget.attrs["class"] = "check-input"


class ProgramResourceForm(forms.ModelForm):
    class Meta:
        model = ProgramResource
        fields = ("program", "title", "description", "file", "external_url",
                  "order")
        widgets = {
            "program": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "file": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "external_url": forms.URLInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }
        help_texts = {
            "file": "Upload a PDF or document, or use an external URL below.",
            "external_url": "Optional public link when the resource lives outside the site.",
        }


class SiteBrandingForm(forms.ModelForm):
    class Meta:
        model = SiteBranding
        fields = (
            "org_name", "short_name", "tagline", "founded_year", "location",
            "contact_email", "contact_phone", "website_url", "footer_blurb",
            "logo", "logo_mark", "favicon", "instagram_url", "linkedin_url",
            "twitter_url", "youtube_url", "facebook_url", "title_font",
            "body_font",
        )
        widgets = {
            "org_name": forms.TextInput(attrs={"class": "form-input"}),
            "short_name": forms.TextInput(attrs={"class": "form-input"}),
            "tagline": forms.TextInput(attrs={"class": "form-input"}),
            "founded_year": forms.TextInput(attrs={"class": "form-input"}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-input"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-input"}),
            "website_url": forms.URLInput(attrs={"class": "form-input"}),
            "footer_blurb": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "logo_mark": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "favicon": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "instagram_url": forms.URLInput(attrs={"class": "form-input"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-input"}),
            "twitter_url": forms.URLInput(attrs={"class": "form-input"}),
            "youtube_url": forms.URLInput(attrs={"class": "form-input"}),
            "facebook_url": forms.URLInput(attrs={"class": "form-input"}),
            "title_font": forms.Select(attrs={"class": "form-input"}),
            "body_font": forms.Select(attrs={"class": "form-input"}),
        }
        labels = {
            "org_name": "Project / organization name",
            "short_name": "Short name",
            "founded_year": "Founded year",
            "contact_email": "Contact email",
            "contact_phone": "Contact phone",
            "website_url": "Website URL",
            "footer_blurb": "Footer profile summary",
            "logo_mark": "Compact logo mark",
            "twitter_url": "X / Twitter URL",
            "title_font": "Title font",
            "body_font": "Body font",
        }


class SpeakerForm(forms.ModelForm):
    class Meta:
        model = Speaker
        fields = ("name", "role", "photo", "featured", "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "role": forms.TextInput(attrs={"class": "form-input"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["featured"].widget.attrs["class"] = "check-input"


class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ("name", "position", "title", "credential", "bio", "photo",
                  "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "position": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "credential": forms.TextInput(attrs={"class": "form-input"}),
            "bio": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }


class SiteStatForm(forms.ModelForm):
    class Meta:
        model = SiteStat
        fields = ("label", "value", "suffix", "order")
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-input"}),
            "value": forms.TextInput(attrs={"class": "form-input"}),
            "suffix": forms.TextInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ("author", "author_role", "source", "quote", "photo",
                  "is_published", "order")
        widgets = {
            "author": forms.TextInput(attrs={"class": "form-input"}),
            "author_role": forms.TextInput(attrs={"class": "form-input"}),
            "source": forms.Select(attrs={"class": "form-input"}),
            "quote": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_published"].widget.attrs["class"] = "check-input"


class GalleryImageForm(forms.ModelForm):
    class Meta:
        model = GalleryImage
        fields = ("caption", "image", "program", "is_published", "order")
        widgets = {
            "caption": forms.TextInput(attrs={"class": "form-input"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "program": forms.Select(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_published"].widget.attrs["class"] = "check-input"


class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ("kind", "title", "body", "is_placeholder")
        widgets = {
            "kind": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "body": forms.Textarea(attrs={"class": "form-input", "rows": 14}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_placeholder"].widget.attrs["class"] = "check-input"
