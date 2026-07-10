from django.contrib import admin
from .models import (AuditLog, CashAccount, CashMovement, Expense,
                     IntegrationSettings, MessageCampaign, MessageDelivery,
                     MessageTemplate, BankReconciliation, Budget, BudgetLine,
                     FiscalPeriod, Fund, JournalEntry, JournalLine, LedgerAccount)


@admin.register(CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "institution_name", "currency",
                    "opening_balance", "statement_balance", "status", "is_primary")
    list_filter = ("account_type", "status", "currency", "is_primary")
    search_fields = ("name", "institution_name", "account_number", "branch", "notes")


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ("movement_date", "title", "account", "direction",
                    "amount", "currency", "status")
    list_filter = ("direction", "category", "status", "currency")
    search_fields = ("title", "counterparty", "reference", "memo",
                     "account__name", "transfer_account__name")
    date_hierarchy = "movement_date"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "title", "category", "payee",
                    "amount", "currency", "status")
    list_filter = ("status", "category", "currency")
    search_fields = ("title", "payee", "description", "reference")
    date_hierarchy = "expense_date"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target", "detail")
    list_filter = ("action",)
    search_fields = ("actor__username", "action", "target", "detail")
    date_hierarchy = "created_at"


@admin.register(IntegrationSettings)
class IntegrationSettingsAdmin(admin.ModelAdmin):
    list_display = ("sms_provider", "sms_enabled", "whatsapp_enabled",
                    "email_enabled", "paystack_enabled", "updated_at")

    def has_add_permission(self, request):
        return not IntegrationSettings.objects.exists()


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_by", "updated_at")
    search_fields = ("name", "subject", "body")


@admin.register(MessageCampaign)
class MessageCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "channel", "audience", "status", "created_by", "created_at", "sent_at")
    list_filter = ("channel", "audience", "status")
    search_fields = ("title", "subject", "body")


@admin.register(MessageDelivery)
class MessageDeliveryAdmin(admin.ModelAdmin):
    list_display = ("campaign", "recipient", "channel", "status", "provider", "sent_at")
    list_filter = ("channel", "status", "provider")
    search_fields = ("recipient", "recipient_name", "provider_reference", "error")


@admin.register(LedgerAccount)
class LedgerAccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "normal_balance", "is_active", "allow_posting")
    list_filter = ("account_type", "is_active", "allow_posting")
    search_fields = ("code", "name", "description")


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "fund_type", "donor", "is_active")
    list_filter = ("fund_type", "is_active")


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_on", "ends_on", "status", "closed_by")
    list_filter = ("status",)


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("number", "entry_date", "description", "fund", "status", "total_debits", "total_credits")
    list_filter = ("status", "fiscal_period", "fund")
    search_fields = ("number", "description", "reference")
    inlines = (JournalLineInline,)


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 1


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("name", "fiscal_period", "fund", "status", "created_by", "approved_by")
    list_filter = ("status", "fiscal_period", "fund")
    inlines = (BudgetLineInline,)


@admin.register(BankReconciliation)
class BankReconciliationAdmin(admin.ModelAdmin):
    list_display = ("account", "statement_date", "statement_balance", "book_balance", "difference", "status")
    list_filter = ("status", "account")
