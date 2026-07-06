from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("reference", "donor_name", "amount", "currency",
                    "channel", "status", "campaign", "created_at")
    list_filter = ("channel", "status", "is_recurring")
    search_fields = ("reference", "donor_name", "donor_email")
    date_hierarchy = "created_at"
