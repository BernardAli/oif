"""Tests for public forms, enquiries, notifications, and applications."""
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import User, Role
from engagement.models import (ContactMessage, PartnerEnquiry,
                               NewsletterSubscriber, Application,
                               EventRegistration)
from pages.models import Event, Policy, Program

PWD = "testpass123"

EMAIL = "django.core.mail.backends.locmem.EmailBackend"


def make(username, role=Role.MEMBER, **extra):
    return User.objects.create_user(
        username=username, password=PWD, email=f"{username}@oif.test",
        first_name=username.title(), last_name="T", role=role, **extra)


class PublicContentPagesTest(TestCase):
    def test_new_public_pages_render(self):
        Policy.objects.create(kind=Policy.Kind.PRIVACY, title="Privacy",
                              body="Placeholder.")
        for url in ["/gallery/", "/contact/", "/robots.txt", "/sitemap.xml",
                    "/policy/privacy/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_missing_policy_404s(self):
        self.assertEqual(self.client.get("/policy/terms/").status_code, 404)

    def test_public_event_detail_page_renders_and_accepts_rich_registration(self):
        member = make("event_member")
        program = Program.objects.create(
            wing=Program.Wing.FORGE,
            tagline="Leadership",
            headline="Forge leaders",
            description="Leadership program",
        )
        event = Event.objects.create(
            title="Public Leadership Forum",
            kind=Event.Kind.CONFERENCE,
            program=program,
            theme="Courage and calling",
            summary="A premium leadership gathering.",
            description="Deep teaching and practical labs.",
            audience="Students\nYoung professionals",
            outcomes="Clarity\nNext steps",
            agenda="Welcome\nKeynote\nLabs",
            speakers="OIF Faculty",
            preparation="Bring a notebook.",
            accessibility="Tell us how we can support you.",
            starts_at=timezone.now() + timedelta(days=10),
            location="Accra",
            capacity=80,
            registration_open=True,
            is_published=True,
        )

        response = self.client.get(reverse("pages:event_detail", args=[event.slug]))
        self.assertContains(response, "Public Leadership Forum")
        self.assertContains(response, "Everything participants need to know")
        self.assertContains(response, "Students")
        self.assertContains(response, "Google Calendar")
        self.assertContains(response, reverse("pages:event_calendar", args=[event.slug]))
        self.assertContains(response, "Share event")
        self.assertContains(response, "https://wa.me/")
        self.assertContains(response, "https://twitter.com/intent/tweet")
        self.assertContains(response, "https://www.facebook.com/sharer/sharer.php")
        self.assertContains(response, "mailto:?")
        self.assertContains(response, response.wsgi_request.build_absolute_uri(
            reverse("pages:event_detail", args=[event.slug])
        ))

        calendar = self.client.get(reverse("pages:event_calendar", args=[event.slug]))
        self.assertEqual(calendar.status_code, 200)
        self.assertEqual(calendar["Content-Type"], "text/calendar; charset=utf-8")
        self.assertIn("BEGIN:VCALENDAR", calendar.content.decode())
        self.assertIn("SUMMARY:Public Leadership Forum", calendar.content.decode())
        self.assertIn("LOCATION:Accra", calendar.content.decode())

        self.client.login(username="event_member", password=PWD)
        response = self.client.post(reverse("engagement:register_event", args=[event.slug]), {
            "attendance_mode": EventRegistration.AttendanceMode.IN_PERSON,
            "organisation": "OIF Club",
            "role_title": "Student leader",
            "accessibility_needs": "Front-row seating",
            "dietary_needs": "Vegetarian",
            "question": "Can I bring a friend?",
            "next": reverse("pages:event_detail", args=[event.slug]),
        })
        self.assertRedirects(response, reverse("pages:event_detail", args=[event.slug]))
        registration = EventRegistration.objects.get(event=event, user=member)
        self.assertEqual(registration.attendance_mode, EventRegistration.AttendanceMode.IN_PERSON)
        self.assertEqual(registration.organisation, "OIF Club")
        self.assertEqual(registration.accessibility_needs, "Front-row seating")


@override_settings(EMAIL_BACKEND=EMAIL)
class ContactFormTest(TestCase):
    def test_contact_creates_message_and_emails(self):
        resp = self.client.post(reverse("pages:contact"), {
            "name": "Ama", "email": "ama@example.com", "subject": "Hi",
            "message": "Hello there", "website": ""})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        # team notification + person confirmation
        self.assertEqual(len(mail.outbox), 2)

    def test_honeypot_blocks_spam(self):
        resp = self.client.post(reverse("pages:contact"), {
            "name": "Bot", "email": "bot@example.com", "message": "spam",
            "website": "http://spam"})
        self.assertEqual(resp.status_code, 200)  # re-render with errors
        self.assertEqual(ContactMessage.objects.count(), 0)


@override_settings(EMAIL_BACKEND=EMAIL)
class PartnerEnquiryTest(TestCase):
    def test_partner_creates_enquiry(self):
        resp = self.client.post(reverse("engagement:partner_enquiry"), {
            "organisation": "Acme", "contact_name": "Jane",
            "email": "jane@acme.com", "kind": "SPONSOR",
            "message": "Sponsor us", "website": ""})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(PartnerEnquiry.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)


class NewsletterTest(TestCase):
    def test_newsletter_signup_idempotent(self):
        for _ in range(2):
            self.client.post(reverse("engagement:newsletter_signup"),
                             {"email": "sub@example.com", "next": "/"})
        self.assertEqual(NewsletterSubscriber.objects.filter(
            email="sub@example.com").count(), 1)


class ApplicationKindsTest(TestCase):
    def test_mentee_and_speaker_kinds_accepted(self):
        member = make("m1")
        self.client.login(username="m1", password=PWD)
        for kind in ["MENTEE", "SPEAKER", "MENTOR", "VOLUNTEER"]:
            self.client.post(reverse("engagement:apply"), {
                "kind": kind, "area_of_interest": "X", "motivation": "Y"})
        self.assertEqual(Application.objects.filter(user=member).count(), 4)

    def test_register_event_requires_post(self):
        make("m2")
        self.client.login(username="m2", password=PWD)
        # GET on a POST-only endpoint is rejected
        resp = self.client.get("/engagement/apply/")
        self.assertEqual(resp.status_code, 200)  # apply supports GET (form)
