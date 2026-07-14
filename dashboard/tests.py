"""Role-compliance smoke tests for the OIF dashboard.

Verifies that each role sees only the dashboard sections and analytics
panels its capabilities permit, and that public pages render.
"""
import json
import os
import tempfile
from datetime import timedelta

from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, Role
from engagement.models import Application, EventRegistration
from pages.models import Event, GalleryImage, Program, ProgramResource, SiteBranding
from pages.models import SiteStat, Speaker, TeamMember
from donations.models import Donation
from engagement.models import MentorshipEnrollment
from dashboard.models import CashAccount, CashMovement, Expense, MessageCampaign


PWD = "testpass123"
EMAIL = "django.core.mail.backends.locmem.EmailBackend"


def make(username, role, **extra):
    return User.objects.create_user(
        username=username, password=PWD, email=f"{username}@oif.test",
        first_name=username.title(), last_name="Test", role=role, **extra)


class PublicPagesTest(TestCase):
    def test_public_pages_render(self):
        for name in ["pages:home", "pages:about", "pages:programs",
                     "pages:leadership", "pages:speakers", "pages:impact",
                     "pages:involved", "pages:donate"]:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, name)

    def test_people_pages_are_split_from_about(self):
        TeamMember.objects.create(
            name="Akosua Mensah",
            position=TeamMember.Position.EXEC_DIRECTOR,
            title="Executive Director",
        )
        Speaker.objects.create(name="Kofi Boateng", role="Conference Speaker")

        about = self.client.get(reverse("pages:about"))
        self.assertContains(about, reverse("pages:leadership"))
        self.assertContains(about, reverse("pages:speakers"))
        self.assertNotContains(about, "Akosua Mensah")
        self.assertNotContains(about, "Kofi Boateng")

        leadership = self.client.get(reverse("pages:leadership"))
        speakers = self.client.get(reverse("pages:speakers"))
        self.assertContains(leadership, "Akosua Mensah")
        self.assertContains(speakers, "Kofi Boateng")

    def test_gallery_images_open_in_lightbox(self):
        GalleryImage.objects.create(
            caption="Conference moment",
            image="gallery/conference-moment.png",
            is_published=True,
        )
        resp = self.client.get(reverse("pages:gallery"))
        self.assertContains(resp, 'class="gallery-lightbox-trigger"')
        self.assertContains(resp, 'data-gallery-src="/media/gallery/conference-moment.png"')
        self.assertContains(resp, 'id="galleryLightbox"')
        self.assertContains(resp, "galleryLightboxImage")

    def test_program_detail_renders_and_is_linked(self):
        Program.objects.create(
            wing=Program.Wing.FORGE,
            tagline="Leadership formation for emerging builders.",
            headline="Build with conviction.",
            description="A practical space for young leaders to grow.",
            is_active=True,
        )
        detail_url = reverse("pages:program_detail", args=["forge"])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "The Forge")
        self.assertContains(resp, "Build with conviction.")

        listing = self.client.get(reverse("pages:programs"))
        self.assertContains(listing, detail_url)

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login", resp.url)


class MutationMethodSafetyTest(TestCase):
    def setUp(self):
        self.admin = make("method_admin", Role.ADMIN, is_staff=True)
        self.member = make("method_member", Role.MEMBER)
        self.event = Event.objects.create(
            title="Method-safe event",
            starts_at=timezone.now() + timedelta(days=1),
        )
        self.registration = EventRegistration.objects.create(
            event=self.event, user=self.member
        )
        self.application = Application.objects.create(
            user=self.member, kind=Application.Kind.VOLUNTEER
        )
        self.donation = Donation.objects.create(
            donor=self.member, amount="20.00", reference="METHOD-SAFE"
        )
        self.client.login(username=self.admin.username, password=PWD)

    def test_state_changing_routes_reject_get(self):
        urls = [
            reverse("dashboard:event_action", args=[self.event.pk, "close"]),
            reverse("dashboard:update_registration", args=[
                self.event.pk, self.registration.pk
            ]),
            reverse("dashboard:donation_action", args=[
                self.donation.pk, "mark-failed"
            ]),
            reverse("dashboard:review_application", args=[
                self.application.pk, "approve"
            ]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)


class RoleAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make("admin_u", Role.ADMIN, is_superuser=True, is_staff=True)
        cls.director = make("director_u", Role.DIRECTOR)
        cls.finance = make("finance_u", Role.FINANCE)
        cls.mentor = make("mentor_u", Role.MENTOR)
        cls.volunteer = make("vol_u", Role.VOLUNTEER)
        cls.member = make("member_u", Role.MEMBER)

    def test_members_page_staff_only(self):
        self.client.login(username="director_u", password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:members")).status_code, 200)
        self.client.logout()

        self.client.login(username="member_u", password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:members")).status_code, 403)
        self.client.logout()

        self.client.login(username="mentor_u", password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:members")).status_code, 403)

    def test_review_application_capability(self):
        app = Application.objects.create(
            user=self.member, kind=Application.Kind.MENTOR,
            status=Application.Status.PENDING)
        url = reverse("dashboard:review_application", args=[app.pk, "approve"])

        self.client.login(username="member_u", password=PWD)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.logout()

        self.client.login(username="director_u", password=PWD)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, Role.MENTOR)

    @override_settings(EMAIL_BACKEND=EMAIL)
    def test_application_approval_sends_acceptance_email_once(self):
        app = Application.objects.create(
            user=self.member, kind=Application.Kind.VOLUNTEER,
            status=Application.Status.PENDING,
        )
        url = reverse("dashboard:review_application", args=[app.pk, "approve"])
        self.client.login(username="director_u", password=PWD)
        self.client.post(url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("has been accepted", mail.outbox[0].subject)
        self.assertIn("Welcome", mail.outbox[0].body)
        self.client.post(url)
        self.assertEqual(len(mail.outbox), 1)

    def test_speaker_application_approval_does_not_promote_to_volunteer(self):
        speaker_applicant = make("speaker_applicant", Role.MEMBER)
        app = Application.objects.create(
            user=speaker_applicant,
            kind=Application.Kind.SPEAKER,
            status=Application.Status.PENDING,
        )

        self.client.login(username="director_u", password=PWD)
        resp = self.client.post(
            reverse("dashboard:review_application", args=[app.pk, "approve"])
        )
        self.assertRedirects(resp, reverse("dashboard:applications"))

        app.refresh_from_db()
        speaker_applicant.refresh_from_db()
        self.assertEqual(app.status, Application.Status.APPROVED)
        self.assertEqual(speaker_applicant.role, Role.MEMBER)

    def _panels(self, username):
        self.client.login(username=username, password=PWD)
        resp = self.client.get(reverse("dashboard:analytics_api"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        ids = {p["id"] for p in data["panels"]}
        self.client.logout()
        return ids

    def test_admin_sees_org_analytics(self):
        ids = self._panels("admin_u")
        self.assertIn("donations_time", ids)
        self.assertIn("member_growth", ids)
        self.assertIn("my_giving", ids)

    def test_director_sees_org_analytics(self):
        ids = self._panels("director_u")
        self.assertIn("donations_time", ids)
        self.assertIn("apps_status", ids)

    def test_mentor_sees_mentee_panel_not_org(self):
        ids = self._panels("mentor_u")
        self.assertIn("mentee_progress", ids)
        self.assertIn("my_giving", ids)
        self.assertNotIn("donations_time", ids)
        self.assertNotIn("member_growth", ids)

    def test_member_sees_only_personal_panel(self):
        ids = self._panels("member_u")
        self.assertEqual(ids, {"my_giving"})

    def test_volunteer_sees_only_personal_panel(self):
        ids = self._panels("vol_u")
        self.assertEqual(ids, {"my_giving"})

    def test_member_nav_hides_admin_links(self):
        self.client.login(username="member_u", password=PWD)
        html = self.client.get(reverse("dashboard:home")).content.decode()
        self.assertNotIn(reverse("dashboard:members"), html)
        self.assertNotIn(reverse("dashboard:reports"), html)

    def test_reports_are_role_compliant_and_exportable(self):
        event = Event.objects.create(
            title="Report Forum",
            starts_at=timezone.now() + timedelta(days=7),
            location="Accra",
            is_published=True,
        )
        EventRegistration.objects.create(event=event, user=self.member)
        Donation.objects.create(
            donor=self.member,
            donor_name="Report Member",
            donor_email="report-member@oif.test",
            amount="450.00",
            channel=Donation.Channel.CARD,
            status=Donation.Status.SUCCESS,
            reference="REPORT-GIFT",
            campaign="Reports Fund",
        )

        self.client.login(username="member_u", password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:reports")).status_code, 403)
        self.client.logout()

        self.client.login(username="admin_u", password=PWD)
        resp = self.client.get(reverse("dashboard:reports"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reports")
        self.assertContains(resp, "Executive")
        self.assertContains(resp, "Finance")
        self.assertContains(resp, "Events")
        self.assertContains(resp, "People")
        self.assertContains(resp, "Content")
        self.assertContains(resp, "Engagement")
        self.assertContains(resp, "reportsChartsData")
        export = self.client.get(reverse("dashboard:reports_export") + "?type=all")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "text/csv")
        body = export.content.decode()
        self.assertIn("finance,income", body)
        self.assertIn("events,registrations", body)
        self.client.logout()

        self.client.login(username="finance_u", password=PWD)
        resp = self.client.get(reverse("dashboard:reports"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Finance report")
        self.assertNotContains(resp, "People report")
        finance_export = self.client.get(reverse("dashboard:reports_export") + "?type=finance")
        self.assertIn("finance,income", finance_export.content.decode())

    def test_dashboard_home_renders_workspace_and_latest_events(self):
        Event.objects.create(
            title="Latest Upcoming Forum",
            starts_at=timezone.now() + timedelta(days=3),
            location="Accra",
            is_published=True,
        )
        self.client.login(username="member_u", password=PWD)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, 'data-home-tab="workspace"')
        self.assertContains(resp, 'data-home-tab="events"')
        self.assertContains(resp, 'id="home-tab-activity"')
        self.assertContains(resp, "Workspace")
        self.assertContains(resp, "Latest Upcoming Events")
        self.assertContains(resp, "Latest Upcoming Forum")
        self.assertContains(resp, "My Activity")

    def test_director_nav_shows_members(self):
        self.client.login(username="director_u", password=PWD)
        html = self.client.get(reverse("dashboard:home")).content.decode()
        self.assertIn(reverse("dashboard:members"), html)

    def test_all_roles_reach_home(self):
        for username in ["admin_u", "director_u", "mentor_u", "vol_u", "member_u"]:
            self.client.login(username=username, password=PWD)
            self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
            self.client.logout()


class CapabilityModelTest(TestCase):
    def test_role_capability_matrix(self):
        member = make("cap_member", Role.MEMBER)
        admin = make("cap_admin", Role.ADMIN)
        self.assertTrue(member.can("register_events"))
        self.assertFalse(member.can("manage_members"))
        self.assertFalse(member.can("view_org_analytics"))
        self.assertTrue(admin.can("manage_members"))
        self.assertTrue(admin.can("view_org_analytics"))


class EventManagementTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = make("event_director", Role.DIRECTOR)
        cls.member = make("event_member", Role.MEMBER)
        cls.program = Program.objects.create(
            wing=Program.Wing.FORGE,
            tagline="Leadership",
            headline="Forge leaders",
            description="Leadership program",
        )
        cls.event = Event.objects.create(
            title="Existing Event",
            kind=Event.Kind.CONFERENCE,
            program=cls.program,
            starts_at=timezone.now() + timedelta(days=7),
            location="Accra",
            capacity=50,
        )
        cls.registration = EventRegistration.objects.create(
            event=cls.event,
            user=cls.member,
            status=EventRegistration.Status.REGISTERED,
        )

    def _event_payload(self, **overrides):
        starts_at = timezone.now() + timedelta(days=21)
        payload = {
            "title": "Admin Managed Summit",
            "kind": Event.Kind.WORKSHOP,
            "program": self.program.pk,
            "theme": "Purpose and impact",
            "description": "A staff-managed event.",
            "starts_at": starts_at.strftime("%Y-%m-%dT%H:%M"),
            "location": "Virtual",
            "capacity": 120,
            "is_virtual": "on",
            "registration_open": "on",
            "is_published": "on",
        }
        payload.update(overrides)
        return payload

    def test_member_cannot_access_event_management_pages(self):
        self.client.login(username="event_member", password=PWD)
        self.assertEqual(
            self.client.get(reverse("dashboard:event_create")).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse("dashboard:event_detail", args=[self.event.pk])).status_code,
            403,
        )

    def test_director_can_create_and_edit_event(self):
        self.client.login(username="event_director", password=PWD)
        resp = self.client.post(
            reverse("dashboard:event_create"),
            data=self._event_payload(),
        )
        event = Event.objects.get(title="Admin Managed Summit")
        self.assertRedirects(resp, reverse("dashboard:event_detail", args=[event.pk]))
        self.assertTrue(event.registration_open)
        self.assertTrue(event.is_published)

        resp = self.client.post(
            reverse("dashboard:event_edit", args=[event.pk]),
            data=self._event_payload(title="Updated Admin Summit", capacity=200),
        )
        event.refresh_from_db()
        self.assertRedirects(resp, reverse("dashboard:event_detail", args=[event.pk]))
        self.assertEqual(event.title, "Updated Admin Summit")
        self.assertEqual(event.capacity, 200)

    def test_event_detail_shows_registration_analytics_and_updates_status(self):
        self.client.login(username="event_director", password=PWD)
        resp = self.client.get(reverse("dashboard:event_detail", args=[self.event.pk]))
        self.assertContains(resp, "Active registrations")
        self.assertContains(resp, "event_member@oif.test")
        self.assertContains(resp, "Registered")
        self.assertContains(resp, "Event analytics")
        self.assertContains(resp, "eventChartsData")
        self.assertContains(resp, "echarts.min.js")
        self.assertContains(resp, "Message registrants")
        self.assertContains(resp, "Event communications")

        resp = self.client.post(
            reverse("dashboard:update_registration", args=[self.event.pk, self.registration.pk]),
            data={"status": EventRegistration.Status.ATTENDED},
        )
        self.assertRedirects(resp, reverse("dashboard:event_detail", args=[self.event.pk]))
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, EventRegistration.Status.ATTENDED)

    def test_event_message_action_prefills_and_links_campaign_to_event(self):
        self.client.login(username="event_director", password=PWD)
        compose_url = reverse("dashboard:campaign_create")
        response = self.client.get(compose_url, {"event": self.event.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial["audience"],
            MessageCampaign.Audience.EVENT,
        )
        self.assertEqual(response.context["form"].initial["event"], self.event)
        self.assertContains(response, "Event communication")
        self.assertContains(response, self.event.title)

        response = self.client.post(compose_url, {
            "title": "Registrant reminder",
            "channel": MessageCampaign.Channel.EMAIL,
            "audience": MessageCampaign.Audience.EVENT,
            "event": self.event.pk,
            "subject": "Event reminder",
            "body": "Hello {first_name}, this is your reminder.",
            "action": "draft",
        })
        campaign = MessageCampaign.objects.get(title="Registrant reminder")
        self.assertEqual(campaign.event, self.event)
        self.assertRedirects(
            response, reverse("dashboard:campaign_detail", args=[campaign.pk])
        )

        detail = self.client.get(
            reverse("dashboard:event_detail", args=[self.event.pk])
        )
        self.assertContains(detail, "Registrant reminder")

    def test_event_list_splits_upcoming_and_archived_for_staff(self):
        Event.objects.create(
            title="Archived Event",
            kind=Event.Kind.OUTREACH,
            program=self.program,
            starts_at=timezone.now() - timedelta(days=30),
            location="Accra",
            registration_open=False,
        )
        self.client.login(username="event_director", password=PWD)
        resp = self.client.get(reverse("dashboard:events"))
        self.assertContains(resp, "Upcoming management")
        self.assertContains(resp, "Existing Event")
        self.assertContains(resp, "Archived events")
        self.assertContains(resp, "Archived Event")


class DonationManagementTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make("donation_admin", Role.ADMIN, is_superuser=True, is_staff=True)
        cls.director = make("donation_director", Role.DIRECTOR)
        cls.member = make("donation_member", Role.MEMBER)
        cls.donation = Donation.objects.create(
            donor=cls.member,
            donor_name="Donation Member",
            donor_email="donation_member@oif.test",
            amount="250.00",
            channel=Donation.Channel.MOMO,
            status=Donation.Status.PENDING,
            reference="OIF-TESTREF",
            campaign="Mentorship Fund",
        )
        cls.success_donation = Donation.objects.create(
            donor=cls.member,
            donor_name="Donation Member",
            donor_email="donation_member@oif.test",
            amount="1000.00",
            channel=Donation.Channel.CARD,
            status=Donation.Status.SUCCESS,
            reference="OIF-INCOME",
            campaign="General Fund",
        )
        cls.paid_expense = Expense.objects.create(
            title="Venue deposit",
            category=Expense.Category.EVENTS,
            payee="Accra Conference Centre",
            amount="300.00",
            status=Expense.Status.PAID,
            expense_date=timezone.localdate(),
            payment_method="Bank transfer",
            reference="EXP-001",
            recorded_by=cls.director,
            approved_by=cls.director,
        )
        cls.draft_expense = Expense.objects.create(
            title="Printing quote",
            category=Expense.Category.MEDIA,
            payee="Print House",
            amount="150.00",
            status=Expense.Status.DRAFT,
            expense_date=timezone.localdate(),
            recorded_by=cls.director,
        )
        cls.bank_account = CashAccount.objects.create(
            name="Main Operating Account",
            account_type=CashAccount.AccountType.BANK,
            institution_name="OIF Bank",
            account_number="1234567890",
            opening_balance="500.00",
            statement_balance="1500.00",
            status=CashAccount.Status.ACTIVE,
            is_primary=True,
            created_by=cls.director,
        )
        cls.cash_account = CashAccount.objects.create(
            name="Programme Petty Cash",
            account_type=CashAccount.AccountType.CASH,
            opening_balance="100.00",
            statement_balance="100.00",
            status=CashAccount.Status.ACTIVE,
            created_by=cls.director,
        )
        cls.cash_movement = CashMovement.objects.create(
            account=cls.bank_account,
            direction=CashMovement.Direction.IN,
            category=CashMovement.Category.DONATION_CLEARING,
            title="Donation clearing",
            amount="1000.00",
            currency="GHS",
            status=CashMovement.Status.POSTED,
            movement_date=timezone.localdate(),
            reference="CASH-001",
            linked_donation=cls.success_donation,
            recorded_by=cls.director,
            approved_by=cls.director,
        )

    def test_donations_dashboard_has_tabs_and_echarts(self):
        self.client.login(username="donation_director", password=PWD)
        resp = self.client.get(reverse("dashboard:donations"))
        self.assertContains(resp, "Giving analytics")
        self.assertContains(resp, "donationChartsData")
        self.assertContains(resp, "echarts.min.js")
        self.assertContains(resp, "Needs attention")
        self.assertContains(resp, "OIF-TESTREF")

    def test_finance_accounting_is_role_compliant_and_exports_csv(self):
        self.client.login(username="donation_member", password=PWD)
        self.assertEqual(
            self.client.get(reverse("dashboard:finance_accounting")).status_code,
            403,
        )
        self.client.logout()

        self.client.login(username="donation_director", password=PWD)
        resp = self.client.get(reverse("dashboard:finance_accounting"))
        self.assertContains(resp, "Finance &amp; Accounting")
        self.assertContains(resp, "Income &amp; Expenditure")
        self.assertContains(resp, "Cash &amp; Bank")
        self.assertContains(resp, "Expenses")
        self.assertContains(resp, "Reconciliation")
        self.assertContains(resp, "OIF-TESTREF")
        self.assertContains(resp, "Venue deposit")
        self.assertContains(resp, "Main Operating Account")
        self.assertContains(resp, "Donation clearing")
        self.assertContains(resp, "GHS 700.00")

        export = self.client.get(reverse("dashboard:finance_export"))
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "text/csv")
        self.assertIn("OIF-TESTREF", export.content.decode())
        self.assertIn("expense", export.content.decode())
        self.assertIn("Venue deposit", export.content.decode())
        self.assertIn("donation clearing", export.content.decode().lower())
        self.assertIn("Main Operating Account", export.content.decode())
        self.assertIn("1000.00", export.content.decode())

    def test_finance_can_create_and_update_expenses(self):
        self.client.login(username="donation_admin", password=PWD)
        resp = self.client.post(reverse("dashboard:expense_create"), data={
            "title": "Transport reimbursement",
            "category": Expense.Category.OPERATIONS,
            "payee": "Volunteer Team",
            "description": "Transport for outreach volunteers.",
            "amount": "125.00",
            "currency": "GHS",
            "status": Expense.Status.DRAFT,
            "expense_date": timezone.localdate().isoformat(),
            "payment_method": "Mobile Money",
            "reference": "EXP-NEW",
        })
        self.assertRedirects(resp, reverse("dashboard:finance_accounting"))
        expense = Expense.objects.get(reference="EXP-NEW")
        self.assertEqual(expense.recorded_by, self.admin)
        self.assertEqual(expense.status, Expense.Status.DRAFT)

        resp = self.client.post(
            reverse("dashboard:expense_action", args=[expense.pk, "pay"])
        )
        self.assertRedirects(resp, reverse("dashboard:finance_accounting"))
        expense.refresh_from_db()
        self.assertEqual(expense.status, Expense.Status.PAID)
        self.assertEqual(expense.approved_by, self.admin)

    def test_finance_can_manage_cash_accounts_and_movements(self):
        self.client.login(username="donation_member", password=PWD)
        self.assertEqual(
            self.client.post(reverse("dashboard:cash_account_create"), data={}).status_code,
            403,
        )
        self.client.logout()

        self.client.login(username="donation_admin", password=PWD)
        resp = self.client.post(reverse("dashboard:cash_account_create"), data={
            "name": "Reserve Bank Account",
            "account_type": CashAccount.AccountType.SAVINGS,
            "institution_name": "Reserve Bank",
            "account_number": "987654321",
            "branch": "Accra",
            "currency": "GHS",
            "opening_balance": "2000.00",
            "opening_balance_date": timezone.localdate().isoformat(),
            "statement_balance": "2000.00",
            "last_reconciled_on": timezone.localdate().isoformat(),
            "status": CashAccount.Status.ACTIVE,
            "is_primary": "",
            "accepts_donations": "on",
            "pays_expenses": "on",
            "notes": "Reserve funds",
        })
        self.assertRedirects(resp, reverse("dashboard:finance_accounting"))
        reserve = CashAccount.objects.get(name="Reserve Bank Account")
        self.assertEqual(reserve.created_by, self.admin)

        resp = self.client.post(reverse("dashboard:cash_movement_create"), data={
            "account": self.bank_account.pk,
            "transfer_account": self.cash_account.pk,
            "direction": CashMovement.Direction.TRANSFER,
            "category": CashMovement.Category.TRANSFER,
            "title": "Petty cash top-up",
            "counterparty": "Internal finance",
            "amount": "200.00",
            "currency": "GHS",
            "movement_date": timezone.localdate().isoformat(),
            "status": CashMovement.Status.DRAFT,
            "reference": "MOVE-001",
            "linked_donation": "",
            "linked_expense": "",
            "memo": "Top up programme cash box.",
        })
        self.assertRedirects(resp, reverse("dashboard:finance_accounting"))
        movement = CashMovement.objects.get(reference="MOVE-001")
        self.assertEqual(movement.recorded_by, self.admin)
        self.assertEqual(movement.status, CashMovement.Status.DRAFT)

        resp = self.client.post(
            reverse("dashboard:cash_movement_action", args=[movement.pk, "post"])
        )
        self.assertRedirects(resp, reverse("dashboard:finance_accounting"))
        movement.refresh_from_db()
        self.assertEqual(movement.status, CashMovement.Status.POSTED)
        self.assertEqual(movement.approved_by, self.admin)

        resp = self.client.get(reverse("dashboard:finance_accounting"))
        self.assertContains(resp, "Petty cash top-up")
        self.assertContains(resp, "GHS 1,300.00")
        self.assertContains(resp, "GHS 300.00")

    def test_member_can_view_own_donation_detail_only(self):
        other = Donation.objects.create(
            donor_name="Guest",
            donor_email="guest@oif.test",
            amount="100.00",
            channel=Donation.Channel.CARD,
            status=Donation.Status.SUCCESS,
            reference="OIF-GUESTREF",
        )
        self.client.login(username="donation_member", password=PWD)
        self.assertEqual(
            self.client.get(reverse("dashboard:donation_detail", args=[self.donation.pk])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("dashboard:donation_detail", args=[other.pk])).status_code,
            403,
        )

    def test_admin_can_mark_donation_success(self):
        self.client.login(username="donation_admin", password=PWD)
        resp = self.client.post(
            reverse("dashboard:donation_action", args=[self.donation.pk, "mark-success"])
        )
        self.assertRedirects(
            resp, reverse("dashboard:donation_detail", args=[self.donation.pk])
        )
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, Donation.Status.SUCCESS)


class MemberManagementTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make("member_admin", Role.ADMIN, is_superuser=True, is_staff=True)
        cls.director = make("member_director", Role.DIRECTOR)
        cls.ops = make("member_ops", Role.DIR_OPS)
        cls.member = make("managed_member", Role.MEMBER, title="Volunteer hopeful")
        cls.program = Program.objects.create(
            wing=Program.Wing.HADASSAH,
            tagline="Purpose",
            headline="Purpose cohort",
            description="Mentorship program",
        )
        cls.event = Event.objects.create(
            title="Member Summit",
            kind=Event.Kind.CONFERENCE,
            program=cls.program,
            starts_at=timezone.now() + timedelta(days=10),
            location="Accra",
        )
        EventRegistration.objects.create(
            event=cls.event,
            user=cls.member,
            status=EventRegistration.Status.REGISTERED,
        )
        Application.objects.create(
            user=cls.member,
            kind=Application.Kind.VOLUNTEER,
            status=Application.Status.PENDING,
            area_of_interest="Events",
        )
        Donation.objects.create(
            donor=cls.member,
            donor_name="Managed Member",
            donor_email="managed_member@oif.test",
            amount="300.00",
            channel=Donation.Channel.CARD,
            status=Donation.Status.SUCCESS,
            reference="OIF-MEMBERPAY",
            campaign="Hadassah Scholarship",
        )

    def test_members_dashboard_has_tabs_echarts_and_paystack(self):
        self.client.login(username="member_director", password=PWD)
        resp = self.client.get(reverse("dashboard:members"))
        self.assertContains(resp, "Member analytics")
        self.assertContains(resp, "memberChartsData")
        self.assertContains(resp, "echarts.min.js")
        self.assertContains(resp, "Paystack giving")
        self.assertContains(resp, "managed_member")

    def test_member_detail_shows_engagement_paystack_and_admin_form(self):
        self.client.login(username="member_director", password=PWD)
        resp = self.client.get(reverse("dashboard:member_detail", args=[self.member.pk]))
        self.assertContains(resp, "member-profile-photo")
        self.assertContains(resp, "Member picture")
        self.assertContains(resp, "Member Summit")
        self.assertContains(resp, "OIF-MEMBERPAY")
        self.assertContains(resp, "memberDetailChartsData")
        self.assertContains(resp, "Paystack-linked giving")
        self.assertContains(resp, "Save member")

    def test_admin_can_update_member_role_and_status(self):
        self.client.login(username="member_admin", password=PWD)
        resp = self.client.post(reverse("dashboard:member_detail", args=[self.member.pk]), data={
            "role": Role.VOLUNTEER,
            "title": "Events Volunteer",
            "location": "Kumasi, Ghana",
            "is_staff": "",
            "is_active": "on",
            "is_public_profile": "on",
        })
        self.assertRedirects(resp, reverse("dashboard:member_detail", args=[self.member.pk]))
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, Role.VOLUNTEER)
        self.assertEqual(self.member.title, "Events Volunteer")
        self.assertTrue(self.member.is_public_profile)

    @override_settings(EMAIL_BACKEND=EMAIL)
    def test_activating_membership_sends_acceptance_email(self):
        applicant = make("pending_member", Role.APPLICANT, is_active=False)
        self.client.login(username="member_admin", password=PWD)
        self.client.post(reverse("dashboard:member_detail", args=[applicant.pk]), data={
            "role": Role.MEMBER,
            "title": "New member",
            "location": "Accra, Ghana",
            "is_active": "on",
            "is_staff": "",
            "is_public_profile": "",
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("membership has been accepted", mail.outbox[0].subject)
        self.assertIn("Username: pending_member", mail.outbox[0].body)

    def test_member_manager_without_user_admin_cannot_change_roles_or_view_payments(self):
        target = make("ops_managed_member", Role.MEMBER, title="New member")
        self.client.login(username="member_ops", password=PWD)
        resp = self.client.get(reverse("dashboard:members"))
        self.assertContains(resp, "Member analytics")
        self.assertNotContains(resp, "Paystack giving")
        self.assertNotContains(resp, "Paystack payment health")

        resp = self.client.get(reverse("dashboard:member_detail", args=[target.pk]))
        self.assertContains(resp, "Member picture")
        self.assertNotContains(resp, "Paystack-linked giving")
        self.assertNotContains(resp, "Django admin access")

        resp = self.client.post(reverse("dashboard:member_detail", args=[target.pk]), data={
            "role": Role.ADMIN,
            "title": "Operations verified",
            "location": "Takoradi, Ghana",
            "is_staff": "on",
            "is_active": "on",
            "is_public_profile": "on",
        })
        self.assertRedirects(resp, reverse("dashboard:member_detail", args=[target.pk]))
        target.refresh_from_db()
        self.assertEqual(target.role, Role.MEMBER)
        self.assertFalse(target.is_staff)
        self.assertEqual(target.title, "Operations verified")

    def test_director_can_upload_member_picture_from_detail_page(self):
        self.client.login(username="member_director", password=PWD)
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                avatar = SimpleUploadedFile(
                    "member.gif",
                    b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;",
                    content_type="image/gif",
                )
                resp = self.client.post(reverse("dashboard:member_detail", args=[self.member.pk]), data={
                    "role": Role.MEMBER,
                    "title": "Volunteer hopeful",
                    "location": "Accra, Ghana",
                    "avatar": avatar,
                    "is_active": "on",
                })
                self.assertRedirects(resp, reverse("dashboard:member_detail", args=[self.member.pk]))
                self.member.refresh_from_db()
                self.assertTrue(self.member.avatar.name.startswith("avatars/member"))

                resp = self.client.get(reverse("dashboard:member_detail", args=[self.member.pk]))
                self.assertContains(resp, "member-profile-photo")
                self.assertContains(resp, self.member.avatar.url)


class FullDashboardControlTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make("control_admin", Role.ADMIN, is_superuser=True, is_staff=True)
        cls.member = make("control_member", Role.MEMBER)
        cls.mentor = make("control_mentor", Role.MENTOR)
        cls.program = Program.objects.create(
            wing=Program.Wing.FORGE,
            tagline="Original",
            headline="Original headline",
            description="Original description",
        )

    def test_admin_can_manage_public_content_from_dashboard(self):
        self.client.login(username="control_admin", password=PWD)
        resp = self.client.get(reverse("dashboard:content"))
        self.assertContains(resp, "Site CMS")
        self.assertContains(resp, "Programs")
        self.assertContains(resp, reverse("dashboard:programs_manage"))
        self.assertContains(resp, reverse("dashboard:resources_manage"))
        self.assertContains(resp, "Speakers")
        self.assertContains(resp, reverse("dashboard:speakers_manage"))

        resp = self.client.post(reverse("dashboard:speaker_create"), data={
            "name": "Dashboard Speaker",
            "role": "Founder",
            "featured": "on",
            "order": 1,
        })
        speaker = Speaker.objects.get(name="Dashboard Speaker")
        self.assertRedirects(
            resp, reverse("dashboard:speaker_edit", args=[speaker.pk])
        )

        resp = self.client.post(reverse("dashboard:program_edit", args=[self.program.pk]), data={
            "wing": Program.Wing.FORGE,
            "tagline": "Updated tagline",
            "headline": "Updated headline",
            "description": "Updated description",
            "accent": "olive",
            "order": 2,
            "is_active": "on",
        })
        self.assertRedirects(
            resp, reverse("dashboard:program_edit", args=[self.program.pk])
        )
        self.program.refresh_from_db()
        self.assertEqual(self.program.headline, "Updated headline")

        resp = self.client.post(reverse("dashboard:resource_create"), data={
            "program": self.program.pk,
            "title": "Mentorship Brief",
            "description": "Overview for applicants",
            "external_url": "https://example.com/brief.pdf",
            "order": 1,
        })
        resource = ProgramResource.objects.get(title="Mentorship Brief")
        self.assertRedirects(
            resp, reverse("dashboard:resource_edit", args=[resource.pk])
        )

    def test_admin_can_delete_program_from_program_cards(self):
        self.client.login(username="control_admin", password=PWD)
        resource = ProgramResource.objects.create(
            program=self.program,
            title="Delete with program",
        )

        resp = self.client.get(reverse("dashboard:programs_manage"))
        self.assertContains(
            resp, reverse("dashboard:program_delete", args=[self.program.pk])
        )
        self.assertContains(resp, "Delete")

        resp = self.client.post(
            reverse("dashboard:program_delete", args=[self.program.pk])
        )
        self.assertRedirects(resp, reverse("dashboard:programs_manage"))
        self.assertFalse(Program.objects.filter(pk=self.program.pk).exists())
        self.assertFalse(ProgramResource.objects.filter(pk=resource.pk).exists())

    def test_admin_can_open_sidebar_content_managers(self):
        self.client.login(username="control_admin", password=PWD)
        for name, label in [
            ("dashboard:programs_manage", "Program wings"),
            ("dashboard:resources_manage", "Uploaded files"),
            ("dashboard:speakers_manage", "Featured"),
            ("dashboard:leadership_manage", "Leadership"),
        ]:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, name)
            self.assertContains(resp, label)

    def test_admin_can_manage_branding_typography_from_dashboard(self):
        self.client.login(username="control_admin", password=PWD)
        branding = SiteBranding.load()

        resp = self.client.get(reverse("dashboard:content"))
        self.assertContains(resp, "Project profile")
        self.assertContains(resp, "Identity")
        self.assertContains(resp, "Logos")
        self.assertContains(resp, "Title font")
        self.assertContains(resp, "Body font")

        resp = self.client.post(reverse("dashboard:content_edit", args=["branding", branding.pk]), data={
            "org_name": "Onesimus Impact Foundation Ghana",
            "short_name": "OIF Ghana",
            "tagline": "Raising leaders for lasting impact",
            "founded_year": "2018",
            "location": "Accra, Ghana",
            "contact_email": "hello@oif.test",
            "contact_phone": "+233 000 000 000",
            "website_url": "https://oif.test",
            "footer_blurb": "A project profile managed from the CMS.",
            "instagram_url": "https://instagram.com/oif",
            "linkedin_url": "https://linkedin.com/company/oif",
            "twitter_url": "https://x.com/oif",
            "youtube_url": "https://youtube.com/@oif",
            "facebook_url": "https://facebook.com/oif",
            "title_font": "Playfair Display",
            "body_font": "Lato",
        })
        self.assertRedirects(
            resp, reverse("dashboard:content_edit", args=["branding", branding.pk])
        )
        branding.refresh_from_db()
        self.assertEqual(branding.org_name, "Onesimus Impact Foundation Ghana")
        self.assertEqual(branding.short_name, "OIF Ghana")
        self.assertEqual(branding.contact_email, "hello@oif.test")
        self.assertEqual(branding.title_font, "Playfair Display")
        self.assertEqual(branding.body_font, "Lato")

        public = self.client.get(reverse("pages:home"))
        self.assertContains(public, "Onesimus Impact Foundation Ghana")
        self.assertContains(public, "Raising leaders for lasting impact")
        self.assertContains(public, "A project profile managed from the CMS.")
        self.assertContains(public, '--font-title: "Playfair Display"')
        self.assertContains(public, '--font-body: "Lato"')

        dashboard = self.client.get(reverse("dashboard:home"))
        self.assertContains(dashboard, "OIF Ghana")
        self.assertContains(dashboard, '--font-title: "Playfair Display"')
        self.assertContains(dashboard, '--font-body: "Lato"')

    def test_admin_can_create_team_and_stats_from_dashboard(self):
        self.client.login(username="control_admin", password=PWD)
        resp = self.client.post(reverse("dashboard:leadership_create"), data={
            "name": "Dashboard Leader",
            "position": TeamMember.Position.DIRECTOR,
            "title": "Director",
            "credential": "Operations",
            "bio": "Leads operations.",
            "order": 1,
        })
        team = TeamMember.objects.get(name="Dashboard Leader")
        self.assertRedirects(
            resp, reverse("dashboard:leadership_edit", args=[team.pk])
        )

        resp = self.client.post(reverse("dashboard:content_create", args=["stats"]), data={
            "label": "Communities served",
            "value": "12",
            "suffix": "+",
            "order": 1,
        })
        stat = SiteStat.objects.get(label="Communities served")
        self.assertRedirects(
            resp, reverse("dashboard:content_edit", args=["stats", stat.pk])
        )

    def test_admin_can_delete_gallery_image_from_dashboard(self):
        self.client.login(username="control_admin", password=PWD)
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                image = GalleryImage.objects.create(
                    caption="Delete me",
                    program=self.program,
                    is_published=True,
                )
                image.image.save(
                    "gallery/delete-me.png",
                    ContentFile(b"sample image"),
                    save=True,
                )
                image_path = image.image.path
                self.assertTrue(os.path.exists(image_path))

                resp = self.client.get(reverse("dashboard:content"))
                self.assertContains(
                    resp,
                    reverse("dashboard:content_delete", args=["gallery", image.pk]),
                )
                self.assertContains(resp, "Delete")

                resp = self.client.post(
                    reverse("dashboard:content_delete", args=["gallery", image.pk])
                )
                self.assertRedirects(resp, reverse("dashboard:content"))
                self.assertFalse(GalleryImage.objects.filter(pk=image.pk).exists())
                self.assertFalse(os.path.exists(image_path))

    def test_admin_can_manage_mentorship_from_dashboard(self):
        self.client.login(username="control_admin", password=PWD)
        resp = self.client.post(reverse("dashboard:mentorship_create"), data={
            "mentee": self.member.pk,
            "mentor": self.mentor.pk,
            "program": self.program.pk,
            "phase": MentorshipEnrollment.Phase.PHASE1,
            "sessions_completed": 2,
            "sessions_total": 12,
        })
        enrollment = MentorshipEnrollment.objects.get(mentee=self.member)
        self.assertRedirects(
            resp, reverse("dashboard:mentorship_edit", args=[enrollment.pk])
        )

        resp = self.client.post(reverse("dashboard:mentorship_edit", args=[enrollment.pk]), data={
            "mentee": self.member.pk,
            "mentor": self.mentor.pk,
            "program": self.program.pk,
            "phase": MentorshipEnrollment.Phase.PHASE2,
            "sessions_completed": 8,
            "sessions_total": 12,
        })
        enrollment.refresh_from_db()
        self.assertRedirects(
            resp, reverse("dashboard:mentorship_edit", args=[enrollment.pk])
        )
        self.assertEqual(enrollment.phase, MentorshipEnrollment.Phase.PHASE2)
        self.assertEqual(enrollment.sessions_completed, 8)


# ==========================================================================
# Contract role-matrix + new admin area tests (Schedule B)
# ==========================================================================
class ContractRoleMatrixTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make("sadmin", Role.ADMIN, is_superuser=True, is_staff=True)
        cls.editor = make("ceditor", Role.CONTENT_EDITOR)
        cls.finance = make("cfinance", Role.FINANCE)
        cls.partners = make("cpartners", Role.DIR_PARTNERSHIPS)
        cls.lead = make("clead", Role.GLOBAL_LEAD)
        cls.event_mgr = make("ceventmgr", Role.EVENT_MANAGER)
        cls.applicant = make("capplicant", Role.APPLICANT)

    def _status(self, user, url_name):
        self.client.login(username=user, password=PWD)
        r = self.client.get(reverse(url_name))
        self.client.logout()
        return r.status_code

    def test_content_editor_manages_content_not_members(self):
        self.assertEqual(self._status("ceditor", "dashboard:content"), 200)
        self.assertEqual(self._status("ceditor", "dashboard:members"), 403)

    def test_finance_manages_donations_not_content(self):
        self.assertEqual(self._status("cfinance", "dashboard:donations"), 200)
        self.assertEqual(self._status("cfinance", "dashboard:finance_accounting"), 200)
        self.assertEqual(self._status("cfinance", "dashboard:content"), 403)

    def test_content_editor_cannot_access_finance_accounting(self):
        self.assertEqual(self._status("ceditor", "dashboard:finance_accounting"), 403)

    def test_partnerships_sees_enquiries(self):
        self.assertEqual(self._status("cpartners", "dashboard:enquiries"), 200)

    def test_global_lead_sees_audit(self):
        self.assertEqual(self._status("clead", "dashboard:audit"), 200)
        # but cannot manage members
        self.assertEqual(self._status("clead", "dashboard:members"), 403)

    def test_event_manager_manages_events_only(self):
        self.assertEqual(self._status("ceventmgr", "dashboard:events"), 200)
        self.assertEqual(self._status("ceventmgr", "dashboard:enquiries"), 403)

    def test_applicant_has_no_admin_access(self):
        for name in ["dashboard:members", "dashboard:content",
                     "dashboard:enquiries", "dashboard:audit"]:
            self.assertEqual(self._status("capplicant", name), 403, name)

    def test_all_roles_reach_dashboard_home(self):
        for u in ["sadmin", "ceditor", "cfinance", "cpartners", "clead",
                  "ceventmgr", "capplicant"]:
            self.assertEqual(self._status(u, "dashboard:home"), 200, u)


class AuditTrailTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make("auditadmin", Role.ADMIN, is_superuser=True, is_staff=True)
        cls.member = make("auditmember", Role.MEMBER)

    def test_donation_status_change_writes_audit(self):
        from donations.models import Donation
        from dashboard.models import AuditLog
        d = Donation.objects.create(donor_name="X", amount=100,
                                    reference="OIF-AUD1",
                                    status=Donation.Status.PENDING)
        self.client.login(username="auditadmin", password=PWD)
        self.client.post(reverse("dashboard:donation_action",
                                 args=[d.pk, "mark-failed"]))
        self.assertTrue(AuditLog.objects.filter(action="donation.status").exists())

    def test_audit_requires_capability(self):
        self.client.login(username="auditmember", password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:audit")).status_code, 403)
