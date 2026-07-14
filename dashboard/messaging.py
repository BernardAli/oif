"""Provider adapters, audience resolution, and tracked campaign delivery."""
import base64
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from engagement.models import EventRegistration, NewsletterSubscriber
from pages.models import SiteBranding
from .models import IntegrationSettings, MessageCampaign, MessageDelivery

logger = logging.getLogger(__name__)


class MessagingError(Exception):
    pass


def _json_request(url, payload, headers=None, timeout=20):
    request = Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read().decode("utf-8")
            return json.loads(data) if data else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise MessagingError(f"Provider rejected the message ({exc.code}): {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise MessagingError("The messaging provider could not be reached.") from exc


def normalize_phone(value):
    phone = "".join(ch for ch in str(value or "") if ch.isdigit() or ch == "+")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if phone.startswith("0") and len(phone) >= 10:
        phone = "+233" + phone[1:]
    return phone


def send_sms(phone, body, config=None):
    config = config or IntegrationSettings.load()
    phone = normalize_phone(phone)
    if not config.sms_enabled:
        raise MessagingError("SMS sending is disabled in Site CMS settings.")
    if not phone:
        raise MessagingError("Recipient has no valid phone number.")
    if config.sms_provider == IntegrationSettings.SmsProvider.ARKESEL:
        if not config.arkesel_api_key:
            raise MessagingError("Arkesel API key is not configured.")
        data = _json_request(config.arkesel_base_url, {
            "sender": config.sms_sender_id, "message": body,
            "recipients": [phone.lstrip("+")],
        }, {"api-key": config.arkesel_api_key})
        return "Arkesel", str(data.get("data") or data.get("message") or "accepted")[:160]
    if not config.hubtel_client_id or not config.hubtel_client_secret:
        raise MessagingError("Hubtel client credentials are not configured.")
    auth = base64.b64encode(
        f"{config.hubtel_client_id}:{config.hubtel_client_secret}".encode()
    ).decode()
    data = _json_request(config.hubtel_base_url, {
        "From": config.sms_sender_id, "To": phone.lstrip("+"), "Content": body,
    }, {"Authorization": f"Basic {auth}"})
    return "Hubtel", str(data.get("MessageId") or data.get("messageId") or "accepted")[:160]


def send_whatsapp(phone, body, config=None):
    config = config or IntegrationSettings.load()
    phone = normalize_phone(phone).lstrip("+")
    if not config.whatsapp_enabled:
        raise MessagingError("WhatsApp sending is disabled in Site CMS settings.")
    if not config.whatsapp_access_token or not config.whatsapp_phone_number_id:
        raise MessagingError("WhatsApp Cloud API credentials are incomplete.")
    data = _json_request(
        f"https://graph.facebook.com/v22.0/{config.whatsapp_phone_number_id}/messages",
        {"messaging_product": "whatsapp", "to": phone, "type": "text",
         "text": {"preview_url": True, "body": body}},
        {"Authorization": f"Bearer {config.whatsapp_access_token}"},
    )
    messages = data.get("messages") or []
    return "WhatsApp Cloud", str(messages[0].get("id") if messages else "accepted")[:160]


def _audience(campaign):
    if campaign.audience == MessageCampaign.Audience.NEWSLETTER:
        return [
            {"name": row.name, "email": row.email, "phone": ""}
            for row in NewsletterSubscriber.objects.filter(is_active=True)
        ]
    if campaign.audience == MessageCampaign.Audience.CUSTOM:
        return [
            {"name": "", "email": item if "@" in item else "", "phone": item if "@" not in item else ""}
            for item in {line.strip() for line in campaign.custom_recipients.splitlines() if line.strip()}
        ]
    users = User.objects.filter(is_active=True)
    recipients = []
    if campaign.audience == MessageCampaign.Audience.MARKETING:
        users = users.filter(marketing_opt_in=True)
    elif campaign.audience == MessageCampaign.Audience.ROLE:
        users = users.filter(role=campaign.role)
    elif campaign.audience == MessageCampaign.Audience.EVENT:
        registrations = EventRegistration.objects.filter(event=campaign.event).exclude(
            status=EventRegistration.Status.CANCELLED
        )
        user_ids = registrations.filter(user__isnull=False).values_list("user_id", flat=True)
        users = users.filter(pk__in=user_ids)
        recipients = [
            {"name": row.guest_name, "first_name": row.guest_name.split(" ")[0],
             "email": row.guest_email, "phone": row.guest_phone}
            for row in registrations.filter(user__isnull=True)
        ]
    recipients.extend([
        {"name": user.get_full_name() or user.username,
         "first_name": user.first_name, "email": user.email, "phone": user.phone}
        for user in users
    ])
    return recipients


def _render(text, recipient):
    branding = SiteBranding.load()
    values = {
        "name": recipient.get("name", ""),
        "first_name": recipient.get("first_name", "") or recipient.get("name", "").split(" ")[0],
        "email": recipient.get("email", ""), "phone": recipient.get("phone", ""),
        "org_name": branding.display_name,
    }
    try:
        return text.format_map(values)
    except (KeyError, ValueError):
        return text


def _channels(campaign):
    if campaign.channel == MessageCampaign.Channel.ALL:
        return [MessageCampaign.Channel.EMAIL, MessageCampaign.Channel.SMS,
                MessageCampaign.Channel.WHATSAPP]
    return [campaign.channel]


def send_campaign(campaign):
    config = IntegrationSettings.load()
    campaign.status = MessageCampaign.Status.PROCESSING
    campaign.save(update_fields=["status"])
    sent = failed = 0
    for recipient in _audience(campaign):
        for channel in _channels(campaign):
            destination = recipient.get("email") if channel == MessageCampaign.Channel.EMAIL else recipient.get("phone")
            delivery = MessageDelivery.objects.create(
                campaign=campaign, channel=channel, recipient=destination or "",
                recipient_name=recipient.get("name", ""),
            )
            if not destination:
                delivery.status = MessageDelivery.Status.SKIPPED
                delivery.error = f"No {channel.lower()} destination available."
                delivery.save(update_fields=["status", "error"])
                continue
            try:
                body = _render(campaign.body, recipient)
                if channel == MessageCampaign.Channel.EMAIL:
                    if not config.email_enabled:
                        raise MessagingError("Email sending is disabled.")
                    delivered = send_mail(
                        _render(campaign.subject or campaign.title, recipient), body,
                        settings.DEFAULT_FROM_EMAIL, [destination], fail_silently=False,
                    )
                    if not delivered:
                        raise MessagingError("Email backend accepted no messages.")
                    provider, reference = "Django email", "accepted"
                elif channel == MessageCampaign.Channel.SMS:
                    provider, reference = send_sms(destination, body, config)
                else:
                    provider, reference = send_whatsapp(destination, body, config)
                delivery.status = MessageDelivery.Status.SENT
                delivery.provider = provider
                delivery.provider_reference = reference
                delivery.sent_at = timezone.now()
                sent += 1
            except Exception as exc:
                logger.warning("Message delivery failed", exc_info=True)
                delivery.status = MessageDelivery.Status.FAILED
                delivery.error = str(exc)[:500]
                failed += 1
            delivery.save()
    campaign.sent_at = timezone.now()
    if sent and failed:
        campaign.status = MessageCampaign.Status.PARTIAL
    elif sent:
        campaign.status = MessageCampaign.Status.SENT
    else:
        campaign.status = MessageCampaign.Status.FAILED
    campaign.save(update_fields=["status", "sent_at"])
    return {"sent": sent, "failed": failed, "skipped": campaign.deliveries.filter(status=MessageDelivery.Status.SKIPPED).count()}
