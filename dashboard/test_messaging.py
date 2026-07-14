from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from engagement.models import EventRegistration
from pages.models import Event
from .forms import IntegrationSettingsForm
from .messaging import send_campaign, send_sms
from .models import (IntegrationSettings, MessageCampaign, MessageDelivery,
                     MessageTemplate)

PWD = "message-test-pass-123"


def user(username, role=Role.MEMBER, **extra):
    return User.objects.create_user(
        username=username, password=PWD, email=f"{username}@example.com",
        role=role, **extra
    )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CampaignDeliveryTest(TestCase):
    def test_personalized_email_campaign_targets_marketing_opt_ins_only(self):
        recipient = user("ama", first_name="Ama", marketing_opt_in=True)
        user("kwame", marketing_opt_in=False)
        campaign = MessageCampaign.objects.create(
            title="Welcome", channel=MessageCampaign.Channel.EMAIL,
            audience=MessageCampaign.Audience.MARKETING,
            subject="Hello {first_name}", body="Hi {name} from {org_name}",
            created_by=recipient,
        )
        result = send_campaign(campaign)
        campaign.refresh_from_db()
        self.assertEqual(result, {"sent": 1, "failed": 0, "skipped": 0})
        self.assertEqual(campaign.status, MessageCampaign.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Hello Ama")
        self.assertEqual(campaign.deliveries.get().status, MessageDelivery.Status.SENT)

    def test_event_campaign_includes_guest_registrants(self):
        sender = user("event_sender", Role.EVENT_MANAGER)
        event = Event.objects.create(
            title="Open Forum", starts_at=timezone.now() + timedelta(days=4)
        )
        EventRegistration.objects.create(
            event=event, guest_name="Guest Attendee",
            guest_email="guest@example.com", guest_phone="+233240000000",
        )
        campaign = MessageCampaign.objects.create(
            title="Event update", channel=MessageCampaign.Channel.EMAIL,
            audience=MessageCampaign.Audience.EVENT, event=event,
            subject="Hello {first_name}", body="An update for {name}",
            created_by=sender,
        )
        result = send_campaign(campaign)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(mail.outbox[0].to, ["guest@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Hello Guest")

    @patch("dashboard.messaging._json_request", return_value={"data": "ark-123"})
    def test_arkesel_adapter_uses_configured_provider(self, request):
        config = IntegrationSettings(
            sms_enabled=True, sms_provider=IntegrationSettings.SmsProvider.ARKESEL,
            sms_sender_id="OIF", arkesel_api_key="secret-key",
        )
        provider, reference = send_sms("0244000000", "Hello", config)
        self.assertEqual(provider, "Arkesel")
        self.assertEqual(reference, "ark-123")
        payload = request.call_args.args[1]
        self.assertEqual(payload["recipients"], ["233244000000"])

    @patch("dashboard.messaging._json_request", return_value={"MessageId": "hub-123"})
    def test_hubtel_adapter_uses_configured_provider(self, request):
        config = IntegrationSettings(
            sms_enabled=True, sms_provider=IntegrationSettings.SmsProvider.HUBTEL,
            sms_sender_id="OIF", hubtel_client_id="client",
            hubtel_client_secret="secret",
        )
        provider, reference = send_sms("+233244000000", "Hello", config)
        self.assertEqual((provider, reference), ("Hubtel", "hub-123"))
        self.assertIn("Authorization", request.call_args.args[2])


class MessagingRoleComplianceTest(TestCase):
    def test_communications_role_can_send_but_cannot_configure_secrets(self):
        comms = user("comms", Role.DIR_COMMS)
        self.client.login(username=comms.username, password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:messaging")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:campaign_create")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:integration_settings")).status_code, 403)

    def test_admin_can_configure_integrations(self):
        admin = user("admin_message", Role.ADMIN)
        self.client.login(username=admin.username, password=PWD)
        response = self.client.get(reverse("dashboard:integration_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integration control centre")
        self.assertContains(response, "Arkesel")
        self.assertContains(response, "Hubtel")
        self.assertContains(response, "WhatsApp Cloud API")
        self.assertContains(response, reverse("donations:webhook"))
        self.assertContains(response, "Save all integrations")

    def test_member_cannot_access_messaging(self):
        member = user("ordinary")
        self.client.login(username=member.username, password=PWD)
        self.assertEqual(self.client.get(reverse("dashboard:messaging")).status_code, 403)

    def test_messaging_dashboard_renders_operations_console_and_filters_campaigns(self):
        comms = user("filter_comms", Role.DIR_COMMS)
        MessageCampaign.objects.create(
            title="Email update", channel=MessageCampaign.Channel.EMAIL,
            audience=MessageCampaign.Audience.ALL_MEMBERS,
            subject="Email subject", body="Email body", created_by=comms,
        )
        MessageCampaign.objects.create(
            title="SMS reminder", channel=MessageCampaign.Channel.SMS,
            audience=MessageCampaign.Audience.EVENT,
            body="SMS body", created_by=comms,
        )
        self.client.login(username=comms.username, password=PWD)
        response = self.client.get(reverse("dashboard:messaging"), {
            "q": "reminder", "channel": MessageCampaign.Channel.SMS,
            "status": MessageCampaign.Status.DRAFT,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "One message. Every channel.")
        self.assertContains(response, "Channel readiness")
        self.assertContains(response, "SMS reminder")
        self.assertNotContains(response, "Email update")

    def test_campaign_composer_renders_guided_workflow_and_saves_draft(self):
        comms = user("composer_comms", Role.DIR_COMMS)
        MessageTemplate.objects.create(
            name="Welcome template", subject="Welcome {first_name}",
            body="Hello {name} from {org_name}", created_by=comms,
        )
        self.client.login(username=comms.username, password=PWD)
        response = self.client.get(reverse("dashboard:campaign_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaign readiness")
        self.assertContains(response, "Message preview")
        self.assertContains(response, "Insert personalization")
        self.assertContains(response, "Welcome template")

        response = self.client.post(reverse("dashboard:campaign_create"), {
            "title": "Monthly update",
            "channel": MessageCampaign.Channel.EMAIL,
            "audience": MessageCampaign.Audience.ALL_MEMBERS,
            "subject": "Hello members",
            "body": "A useful platform update.",
            "action": "draft",
        })
        campaign = MessageCampaign.objects.get(title="Monthly update")
        self.assertEqual(campaign.status, MessageCampaign.Status.DRAFT)
        self.assertRedirects(
            response, reverse("dashboard:campaign_detail", args=[campaign.pk])
        )


class IntegrationSecretFormTest(TestCase):
    def test_blank_secret_fields_preserve_existing_credentials(self):
        config = IntegrationSettings.objects.create(
            arkesel_api_key="keep-me", paystack_secret_key="keep-paystack"
        )
        data = {
            "sms_provider": IntegrationSettings.SmsProvider.ARKESEL,
            "sms_sender_id": "OIF", "arkesel_base_url": config.arkesel_base_url,
            "hubtel_base_url": config.hubtel_base_url, "email_enabled": "on",
            "email_from_name": "OIF",
        }
        form = IntegrationSettingsForm(data, instance=config)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.arkesel_api_key, "keep-me")
        self.assertEqual(saved.paystack_secret_key, "keep-paystack")


class MessageTemplateTest(TestCase):
    def test_template_can_supply_campaign_subject_and_body(self):
        template = MessageTemplate.objects.create(
            name="Reminder", subject="Reminder", body="Hello {name}"
        )
        from .forms import MessageCampaignForm
        form = MessageCampaignForm({
            "title": "Reminder run", "channel": MessageCampaign.Channel.EMAIL,
            "audience": MessageCampaign.Audience.ALL_MEMBERS,
            "template": template.pk, "subject": "", "body": "",
        })
        self.assertTrue(form.is_valid(), form.errors)
        campaign = form.save()
        self.assertEqual((campaign.subject, campaign.body), ("Reminder", "Hello {name}"))
