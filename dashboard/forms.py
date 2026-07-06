from django import forms

from accounts.models import User
from engagement.models import MentorshipEnrollment
from pages.models import (Event, Program, ProgramResource, SiteBranding,
                          SiteStat, Speaker, TeamMember, Testimonial,
                          GalleryImage, Policy)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("is_active", "is_staff", "is_public_profile"):
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
