from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target", "detail")
    list_filter = ("action",)
    search_fields = ("actor__username", "action", "target", "detail")
    date_hierarchy = "created_at"
