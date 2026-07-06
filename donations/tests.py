"""Donation flow tests: demo success, receipt email, donor note."""
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from donations.models import Donation

EMAIL = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=EMAIL)
class DonationFlowTest(TestCase):
    def test_demo_donation_success_sends_receipt(self):
        resp = self.client.post(reverse("donations:give"), {
            "donor_name": "Kojo", "donor_email": "kojo@example.com",
            "amount": "200.00", "channel": "MOMO", "campaign": "General Fund",
            "note": "In honour of Mum", "is_recurring": ""}, follow=True)
        self.assertEqual(resp.status_code, 200)
        d = Donation.objects.get()
        self.assertEqual(d.status, Donation.Status.SUCCESS)
        self.assertEqual(d.amount, Decimal("200.00"))
        self.assertEqual(d.note, "In honour of Mum")
        self.assertTrue(d.receipt_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("receipt", mail.outbox[0].subject.lower())

    def test_status_page_renders(self):
        d = Donation.objects.create(
            donor_name="A", donor_email="a@x.com", amount=Decimal("50.00"),
            reference="OIF-TEST123", status=Donation.Status.SUCCESS)
        resp = self.client.get(reverse("donations:status", args=[d.reference]))
        self.assertEqual(resp.status_code, 200)
