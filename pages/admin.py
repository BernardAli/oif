from django.contrib import admin
from .models import (Program, ProgramResource, Speaker, TeamMember, SiteStat,
                     Event, Testimonial, GalleryImage, Policy, SiteBranding)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("get_wing_display", "tagline", "accent", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "featured", "order")
    list_editable = ("featured", "order")
    search_fields = ("name", "role")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "title", "order")
    list_editable = ("order",)
    list_filter = ("position",)


@admin.register(SiteStat)
class SiteStatAdmin(admin.ModelAdmin):
    list_display = ("value", "suffix", "label", "order")
    list_editable = ("order",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "program", "starts_at",
                    "registration_open", "is_published", "registration_count")
    list_filter = ("kind", "registration_open", "is_published")
    search_fields = ("title", "theme")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "starts_at"
    fieldsets = (
        ("Core", {
            "fields": ("title", "slug", "kind", "program", "theme", "summary",
                       "description", "flyer"),
        }),
        ("Public event detail", {
            "fields": ("audience", "outcomes", "agenda", "speakers",
                       "preparation", "accessibility"),
        }),
        ("Logistics", {
            "fields": ("starts_at", "location", "venue_address", "online_url",
                       "is_virtual", "capacity"),
        }),
        ("Registration", {
            "fields": ("registration_note", "contact_email",
                       "registration_open", "is_published"),
        }),
    )


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author", "source", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("source", "is_published")
    search_fields = ("author", "quote")


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("caption", "program", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_published", "program")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "is_placeholder", "updated_at")
    list_filter = ("kind", "is_placeholder")


class ProgramResourceInline(admin.TabularInline):
    model = ProgramResource
    extra = 1


@admin.register(ProgramResource)
class ProgramResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "program", "order")
    list_filter = ("program",)


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
    list_display = ("org_name", "short_name", "title_font", "body_font", "updated_at")
    fieldsets = (
        ("Project profile", {
            "fields": (
                "org_name", "short_name", "tagline", "founded_year", "location",
                "contact_email", "contact_phone", "website_url", "footer_blurb",
            )
        }),
        ("Logos", {"fields": ("logo", "logo_mark", "favicon")}),
        ("Social links", {
            "fields": (
                "instagram_url", "linkedin_url", "twitter_url",
                "youtube_url", "facebook_url",
            )
        }),
        ("Typography", {"fields": ("title_font", "body_font")}),
    )

    def has_add_permission(self, request):
        return not SiteBranding.objects.exists()
