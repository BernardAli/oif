from datetime import timedelta

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .checks import production_configuration_check
from .models import (ConferenceEdition, Event, MentorshipSession,
                     MentorshipTrack, Policy, Program, ProgramInitiative,
                     SiteBranding)
from .views import error_500


class PublicPageBehaviourTest(TestCase):
    def test_program_mega_nav_only_shows_active_database_programs(self):
        active = Program.objects.create(
            wing=Program.Wing.FORGE,
            tagline="Active leadership pathway",
            headline="Forge leaders",
            description="Active program",
            is_active=True,
        )
        Program.objects.create(
            wing=Program.Wing.HADASSAH,
            tagline="Hidden pathway",
            headline="Hidden program",
            description="Inactive program",
            is_active=False,
        )

        response = self.client.get(reverse("pages:home"))
        self.assertContains(
            response, reverse("pages:program_detail", args=[active.wing.lower()])
        )
        self.assertContains(response, "Active leadership pathway")
        self.assertNotContains(response, "Hidden pathway")
        self.assertNotContains(response, "Open Events")

    def test_unpublished_event_is_not_public(self):
        event = Event.objects.create(
            title="Private planning event",
            starts_at=timezone.now() + timedelta(days=2),
            is_published=False,
        )
        response = self.client.get(reverse("pages:event_detail", args=[event.slug]))
        self.assertEqual(response.status_code, 404)

    def test_inactive_program_detail_is_not_public(self):
        program = Program.objects.create(
            wing=Program.Wing.FORGE,
            tagline="Hidden",
            headline="Hidden program",
            description="Not ready for publication.",
            is_active=False,
        )
        response = self.client.get(
            reverse("pages:program_detail", args=[program.wing.lower()])
        )
        self.assertEqual(response.status_code, 404)

    def test_branding_singleton_is_reused(self):
        first = SiteBranding.load()
        first.org_name = "OIF Test"
        first.save()
        second = SiteBranding.load()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.org_name, "OIF Test")
        self.assertEqual(SiteBranding.objects.count(), 1)

    def test_policy_body_is_rendered(self):
        # Privacy policy already exists via migration 0009 - update it in
        # place rather than creating a second row (kind is unique).
        Policy.objects.update_or_create(
            kind=Policy.Kind.PRIVACY,
            defaults={
                "title": "Privacy",
                "body": "We protect participant data.",
                "is_placeholder": False,
            },
        )
        response = self.client.get(reverse("pages:policy", args=["privacy"]))
        self.assertContains(response, "We protect participant data.")

    def test_privacy_terms_and_donation_policies_exist_out_of_the_box(self):
        """A fresh database (migrations only, no seed_demo) must already have
        working Privacy, Terms, and Donation Policy pages — the footer links
        to all three unconditionally and must never 404."""
        for kind in ["privacy", "terms", "donation"]:
            self.assertTrue(
                Policy.objects.filter(kind=kind).exists(), f"missing seeded {kind} policy"
            )
            response = self.client.get(reverse("pages:policy", args=[kind]))
            self.assertEqual(response.status_code, 200, kind)

        footer = self.client.get(reverse("pages:home"))
        for kind in ["privacy", "terms", "donation"]:
            self.assertContains(footer, reverse("pages:policy", args=[kind]))


class ProgramInitiativeStructureTest(TestCase):
    def test_required_six_initiative_pages_are_seeded(self):
        expected = {
            "the-emerging-leader", "the-emerging-lady",
            "forge-mentorship-program", "bloom-360-mentorship-program",
            "onesimus-community-outreach-initiative",
            "in-person-events-and-gatherings",
        }
        self.assertEqual(
            set(ProgramInitiative.objects.values_list("slug", flat=True)), expected
        )

    def test_programs_page_uses_three_required_pillars(self):
        response = self.client.get(reverse("pages:programs"))
        self.assertContains(response, "Programs &amp; Initiatives")
        self.assertContains(response, "Three distinct pillars. One mission")
        self.assertContains(response, "Virtual Conferences")
        self.assertContains(response, "Mentorship Program")
        self.assertContains(response, "Events")
        for initiative in ProgramInitiative.objects.all():
            self.assertContains(
                response, reverse("pages:initiative_detail", args=[initiative.slug])
            )

    def test_conference_pages_share_upcoming_and_archive_structure(self):
        for slug in ("the-emerging-leader", "the-emerging-lady"):
            response = self.client.get(reverse("pages:initiative_detail", args=[slug]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Upcoming Conference")
            self.assertContains(response, "Past Conferences")

    def test_mentorship_pages_seed_eight_sessions_and_phase_two(self):
        for slug in ("forge-mentorship-program", "bloom-360-mentorship-program"):
            initiative = ProgramInitiative.objects.get(slug=slug)
            self.assertEqual(
                MentorshipSession.objects.filter(initiative=initiative).count(), 8
            )
            self.assertTrue(MentorshipTrack.objects.filter(initiative=initiative).exists())
            response = self.client.get(
                reverse("pages:initiative_detail", args=[initiative.slug])
            )
            self.assertContains(response, "Watch · Coming soon", count=8)
            self.assertContains(response, "Phase 2")

    def test_published_conference_edition_appears_on_public_page(self):
        initiative = ProgramInitiative.objects.get(slug="the-emerging-leader")
        ConferenceEdition.objects.create(
            initiative=initiative, status=ConferenceEdition.Status.UPCOMING,
            name="Leadership Across Frontiers", description="Theme and speaker details.",
            registration_url="https://forms.google.com/example",
        )
        response = self.client.get(
            reverse("pages:initiative_detail", args=[initiative.slug])
        )
        self.assertContains(response, "Leadership Across Frontiers")
        self.assertContains(response, "Register via Google Form")


class DeploymentConfigurationCheckTest(SimpleTestCase):
    @override_settings(
        DEBUG=False,
        SECRET_KEY="django-insecure-dev-key-change-me",
        PAYSTACK_DEMO_MODE=True,
        PAYSTACK_SECRET_KEY="",
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
    )
    def test_unsafe_production_configuration_is_reported(self):
        issues = production_configuration_check(None)
        ids = {issue.id for issue in issues}
        self.assertTrue({"oif.E001", "oif.E002", "oif.W002", "oif.W003"} <= ids)

    @override_settings(
        DEBUG=False,
        SECRET_KEY="a-long-production-secret-that-is-not-the-development-key",
        PAYSTACK_DEMO_MODE=False,
        PAYSTACK_SECRET_KEY="sk_live_configured",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    )
    def test_safe_production_configuration_has_no_oif_issues(self):
        self.assertEqual(production_configuration_check(None), [])


class ErrorPageTest(TestCase):
    @override_settings(DEBUG=False)
    def test_custom_404_page(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page isn’t here.", status_code=404)

    @override_settings(DEBUG=False)
    def test_custom_500_page(self):
        response = error_500(RequestFactory().get("/broken/"))
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "We couldn’t complete that request.", status_code=500)
