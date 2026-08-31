from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .checks import production_configuration_check
from .models import (BRAND_COLOR_PALETTES, ConferenceEdition, Event, MentorshipSession,
                     MentorshipTrack, Policy, Program, ProgramInitiative,
                     SiteBranding, SitePageCopy)
from .views import error_500


class BrandPaletteCoverageTest(SimpleTestCase):
    @staticmethod
    def _luminance(hex_color):
        channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92 if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def _contrast(self, first, second):
        first_luminance = self._luminance(first)
        second_luminance = self._luminance(second)
        return (max(first_luminance, second_luminance) + 0.05) / (
            min(first_luminance, second_luminance) + 0.05
        )

    def test_all_seventeen_palettes_have_unique_names_and_aa_contrast(self):
        self.assertEqual(len(BRAND_COLOR_PALETTES), 17)
        self.assertEqual(
            len({palette["value"] for palette in BRAND_COLOR_PALETTES}), 17
        )
        for palette in BRAND_COLOR_PALETTES:
            colors = palette["colors"]
            with self.subTest(palette=palette["value"]):
                self.assertGreaterEqual(
                    self._contrast(colors["coffee"], colors["cream"]), 4.5
                )
                self.assertGreaterEqual(
                    self._contrast(colors["dark"], colors["cream"]), 4.5
                )
                self.assertGreaterEqual(
                    self._contrast(colors["tan"], colors["dark"]), 4.5
                )

    def test_oif_deliverables_palette_uses_approved_colors(self):
        palette = next(
            item for item in BRAND_COLOR_PALETTES
            if item["value"] == "oif_deliverables"
        )
        self.assertEqual(palette["colors"], {
            "ink": "#141413",
            "ink_soft": "#6B5B4E",
            "paper": "#FFFFFF",
            "paper_2": "#F1E8DE",
            "cream": "#FAF5EF",
            "coffee": "#8A5A34",
            "coffee_deep": "#6E4527",
            "coffee_soft": "#C49A6C",
            "tan": "#C49A6C",
            "dark": "#141413",
            "line": "rgba(20, 20, 19, 0.12)",
            "line_strong": "rgba(20, 20, 19, 0.26)",
        })

    def test_onesimus_logo_palette_uses_sampled_brand_colors(self):
        palette = next(
            item for item in BRAND_COLOR_PALETTES
            if item["value"] == "onesimus_logo"
        )
        self.assertEqual(palette["colors"]["coffee"], "#0A0F4D")
        self.assertEqual(palette["colors"]["coffee_deep"], "#040743")
        self.assertEqual(palette["colors"]["tan"], "#D6A529")
        self.assertEqual(palette["colors"]["paper"], "#FFFFFF")

    def test_brand_rules_and_charts_do_not_bypass_dynamic_palette(self):
        css = (Path(settings.BASE_DIR) / "static/css/site.css").read_text(
            encoding="utf-8"
        )
        # The first :root block is a safe no-JavaScript/default fallback. All
        # actual component rules after it must use the runtime variables.
        component_rules = css.split("* {", 1)[1]
        chart_template = (
            Path(settings.BASE_DIR) / "templates/dashboard/_echarts_theme.html"
        ).read_text(encoding="utf-8")
        forbidden = (
            "#1a1512", "#6f6151", "#6f4a2f", "#52341f", "#9a6b48",
            "#cda983", "#211a14", "rgba(26,21,18", "rgba(111,74,47",
        )
        for literal in forbidden:
            self.assertNotIn(literal, component_rules.lower())
            self.assertNotIn(literal, chart_template.lower())


class PublicPageBehaviourTest(TestCase):
    def test_program_mega_nav_shows_pillars_and_active_initiatives(self):
        active = ProgramInitiative.objects.create(
            pillar=ProgramInitiative.Pillar.CONFERENCES,
            page_type=ProgramInitiative.PageType.CONFERENCE,
            title="Active leadership conference",
            eyebrow="The Forge Initiative",
            description="Active initiative",
            is_active=True,
        )
        inactive = ProgramInitiative.objects.create(
            pillar=ProgramInitiative.Pillar.EVENTS,
            page_type=ProgramInitiative.PageType.IN_PERSON,
            title="Hidden community gathering",
            eyebrow="Unpublished initiative",
            description="Inactive initiative",
            is_active=False,
        )

        response = self.client.get(reverse("pages:home"))
        self.assertContains(
            response, reverse("pages:initiative_detail", args=[active.slug])
        )
        self.assertContains(response, "Active leadership conference")
        self.assertNotContains(response, inactive.title)
        for pillar in ("Virtual Conferences", "Mentorship Program", "Events"):
            self.assertContains(response, pillar)
        for initiative in ProgramInitiative.objects.filter(is_active=True):
            self.assertContains(
                response, reverse("pages:initiative_detail", args=[initiative.slug])
            )

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
        self.assertContains(
            response,
            "Our flagship biannual virtual gatherings under The Forge and "
            "The Hadassah Project.",
        )
        self.assertContains(
            response,
            "Structured, two-phase mentorship cohorts under The Forge and "
            "The Hadassah Project.",
        )
        self.assertContains(
            response,
            "In-person events, gatherings, and our humanitarian community outreach.",
        )
        self.assertContains(response, "Explore conferences →")
        self.assertContains(response, "Explore mentorship →")
        self.assertContains(response, "Explore events →")
        for initiative in ProgramInitiative.objects.all():
            self.assertContains(
                response, reverse("pages:initiative_detail", args=[initiative.slug])
            )

    def test_programs_document_copy_is_editable_from_page_copy_cms(self):
        page_copy = SitePageCopy.load()
        page_copy.programs_hero_body = "A custom programs introduction."
        page_copy.programs_conferences_body = "A custom conference introduction."
        page_copy.programs_events_body = "A custom events introduction."
        page_copy.save()

        response = self.client.get(reverse("pages:programs"))
        self.assertContains(response, "A custom programs introduction.")
        self.assertContains(response, "A custom conference introduction.")
        self.assertContains(response, "A custom events introduction.")

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

        forge = self.client.get(
            reverse("pages:initiative_detail", args=["forge-mentorship-program"])
        )
        self.assertContains(forge, "<b>4 live sessions</b>", count=2, html=True)
        bloom = self.client.get(
            reverse("pages:initiative_detail", args=["bloom-360-mentorship-program"])
        )
        self.assertContains(
            bloom,
            "<b>4 sessions across weeks 9–12</b>",
            count=1,
            html=True,
        )

    def test_event_archives_explain_the_document_fields_when_empty(self):
        outreach = self.client.get(
            reverse(
                "pages:initiative_detail",
                args=["onesimus-community-outreach-initiative"],
            )
        )
        self.assertContains(outreach, "activity number or label")
        self.assertContains(outreach, "number of people impacted")

        gatherings = self.client.get(
            reverse(
                "pages:initiative_detail",
                args=["in-person-events-and-gatherings"],
            )
        )
        self.assertContains(gatherings, "event number or label")
        self.assertContains(gatherings, "venue, date, activity summary, and attendee count")

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
