from django.contrib import admin
from .models import (EventRegistration, Application, MentorshipEnrollment,
                     ContactMessage, PartnerEnquiry, NewsletterSubscriber)


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("attendee_name", "attendee_email", "event", "attendance_mode", "status", "created_at")
    list_filter = ("status", "attendance_mode", "event")
    search_fields = ("user__username", "user__email", "guest_name", "guest_email", "event__title",
                     "organisation", "role_title")
    readonly_fields = ("created_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "status", "area_of_interest", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("user__username", "area_of_interest")


@admin.register(MentorshipEnrollment)
class MentorshipEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("mentee", "mentor", "program", "phase",
                    "sessions_completed", "sessions_total", "progress_pct")
    list_filter = ("phase",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "email", "subject", "message")


@admin.register(PartnerEnquiry)
class PartnerEnquiryAdmin(admin.ModelAdmin):
    list_display = ("organisation", "contact_name", "kind", "status", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("organisation", "contact_name", "email")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("email", "name")
