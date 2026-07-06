from django import forms
from .models import (Application, ContactMessage, EventRegistration,
                     PartnerEnquiry, NewsletterSubscriber)


class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = (
            "attendance_mode", "organisation", "role_title",
            "accessibility_needs", "dietary_needs", "question",
        )
        widgets = {
            "attendance_mode": forms.Select(attrs={"class": "form-input"}),
            "organisation": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Organisation, school, church, or company"}),
            "role_title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Student, founder, volunteer, pastor, etc."}),
            "accessibility_needs": forms.Textarea(attrs={
                "class": "form-input", "rows": 3,
                "placeholder": "Accessibility, interpretation, seating, or mobility needs"}),
            "dietary_needs": forms.Textarea(attrs={
                "class": "form-input", "rows": 3,
                "placeholder": "Dietary notes if meals or refreshments are provided"}),
            "question": forms.Textarea(attrs={
                "class": "form-input", "rows": 3,
                "placeholder": "Anything you want the event team to know?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attendance_mode"].required = False

    def clean_attendance_mode(self):
        return self.cleaned_data.get("attendance_mode") or EventRegistration.AttendanceMode.EITHER


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("kind", "area_of_interest", "motivation")
        widgets = {
            "kind": forms.Select(attrs={"class": "form-input"}),
            "area_of_interest": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. Programs, Media, Finance, Coaching"}),
            "motivation": forms.Textarea(attrs={
                "class": "form-input", "rows": 4,
                "placeholder": "Why do you want to serve with OIF?"}),
        }


class ContactForm(forms.ModelForm):
    # Honeypot: real people leave it empty; bots often fill every field.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input",
                                           "placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"class": "form-input",
                                             "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input",
                                            "placeholder": "+233 …"}),
            "subject": forms.TextInput(attrs={"class": "form-input",
                                              "placeholder": "How can we help?"}),
            "message": forms.Textarea(attrs={"class": "form-input", "rows": 5,
                                             "placeholder": "Your message"}),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class PartnerEnquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = PartnerEnquiry
        fields = ("organisation", "contact_name", "email", "phone", "kind",
                  "message")
        widgets = {
            "organisation": forms.TextInput(attrs={"class": "form-input",
                                                   "placeholder": "Organisation"}),
            "contact_name": forms.TextInput(attrs={"class": "form-input",
                                                   "placeholder": "Contact person"}),
            "email": forms.EmailInput(attrs={"class": "form-input",
                                             "placeholder": "you@org.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input",
                                            "placeholder": "+233 …"}),
            "kind": forms.Select(attrs={"class": "form-input"}),
            "message": forms.Textarea(attrs={"class": "form-input", "rows": 4,
                                             "placeholder": "Tell us how you'd "
                                             "like to partner with OIF"}),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ("email", "name")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-input",
                                             "placeholder": "Your email"}),
            "name": forms.TextInput(attrs={"class": "form-input",
                                           "placeholder": "Name (optional)"}),
        }
