"""Donation flow tests: demo success, receipt email, donor note."""
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
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
        session = self.client.session
        session["donation_references"] = [d.reference]
        session.save()

        resp = self.client.get(reverse("donations:status", args=[d.reference]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "GHS 50.00")

    @override_settings(PAYSTACK_DEMO_MODE=False, PAYSTACK_SECRET_KEY="")
    def test_missing_paystack_configuration_fails_closed_outside_demo_mode(self):
        response = self.client.post(reverse("donations:give"), {
            "donor_name": "Kojo", "donor_email": "kojo@example.com",
            "amount": "200.00", "channel": "MOMO", "campaign": "General Fund",
        })
        donation = Donation.objects.get()
        self.assertEqual(donation.status, Donation.Status.FAILED)
        self.assertFalse(donation.receipt_sent)
        self.assertRedirects(
            response, reverse("donations:status", args=[donation.reference])
        )

    @patch("oif_site.notify.send_mail", return_value=0)
    def test_receipt_is_not_marked_sent_when_backend_delivers_nothing(self, _send):
        response = self.client.post(reverse("donations:give"), {
            "donor_name": "Kojo", "donor_email": "kojo@example.com",
            "amount": "50.00", "channel": "MOMO", "campaign": "General Fund",
        })
        self.assertEqual(response.status_code, 302)
        donation = Donation.objects.get()
        self.assertEqual(donation.status, Donation.Status.SUCCESS)
        self.assertFalse(donation.receipt_sent)

    def test_status_page_rejects_unowned_reference(self):
        d = Donation.objects.create(
            donor_name="A", donor_email="a@x.com", amount=Decimal("50.00"),
            reference="OIF-PRIVATE", status=Donation.Status.SUCCESS)

        resp = self.client.get(reverse("donations:status", args=[d.reference]))
        self.assertEqual(resp.status_code, 403)

    def test_authenticated_donor_can_view_own_status(self):
        user = User.objects.create_user(
            username="donor_user",
            email="donor@example.com",
            password="donor-pass-12345",
        )
        d = Donation.objects.create(
            donor=user, donor_name="Donor", donor_email=user.email,
            amount=Decimal("75.00"), reference="OIF-OWNER",
            status=Donation.Status.SUCCESS)

        self.client.login(username="donor_user", password="donor-pass-12345")
        resp = self.client.get(reverse("donations:status", args=[d.reference]))
        self.assertEqual(resp.status_code, 200)

    @patch("donations.views.paystack.verify_transaction")
    @patch("donations.views.paystack.is_configured", return_value=True)
    def test_callback_does_not_mark_success_when_paystack_details_mismatch(
        self, _configured, verify_transaction
    ):
        d = Donation.objects.create(
            donor_name="A", donor_email="a@x.com", amount=Decimal("50.00"),
            reference="OIF-MISMATCH", status=Donation.Status.PENDING)
        verify_transaction.return_value = {
            "status": "success",
            "reference": d.reference,
            "amount": 4900,
            "currency": "GHS",
            "metadata": {"donation_id": d.pk},
        }

        resp = self.client.get(
            reverse("donations:callback"),
            {"reference": d.reference},
        )
        self.assertRedirects(resp, reverse("donations:status", args=[d.reference]))

        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.PENDING)
        self.assertFalse(d.receipt_sent)

    @override_settings(PAYSTACK_SECRET_KEY="webhook-secret", PAYSTACK_DEMO_MODE=False)
    def test_signed_webhook_automatically_confirms_matching_donation(self):
        donation = Donation.objects.create(
            donor_name="Ama", donor_email="ama@example.com", amount=Decimal("50.00"),
            currency="GHS", reference="OIF-WEBHOOK", status=Donation.Status.PENDING,
        )
        payload = json.dumps({
            "event": "charge.success",
            "data": {"status": "success", "reference": donation.reference,
                     "amount": 5000, "currency": "GHS",
                     "metadata": {"donation_id": donation.pk}},
        }).encode()
        signature = hmac.new(b"webhook-secret", payload, hashlib.sha512).hexdigest()
        response = self.client.post(
            reverse("donations:webhook"), payload,
            content_type="application/json", HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.SUCCESS)

    def test_unsigned_webhook_is_rejected(self):
        response = self.client.post(
            reverse("donations:webhook"), b"{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
